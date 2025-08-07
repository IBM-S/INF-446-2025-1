import os
from flask import Flask, request, jsonify, send_from_directory
import subprocess, glob

app = Flask(__name__, static_url_path='')

@app.route("/")
def main():
    return send_from_directory(".", "main.html")

def get_non_dominated(points):
    dominated = set()
    for i in range(len(points)):
        for j in range(len(points)):
            if i != j:
                if all(points[j][k] <= points[i][k] for k in range(2)) and any(points[j][k] < points[i][k] for k in range(2)):
                    dominated.add(i)
                    break
    return [pt for i, pt in enumerate(points) if i not in dominated]

def parse_instance_name(filename):
    return os.path.splitext(os.path.basename(filename))[0]

def save_front_to_file(points, filepath):
    rounded = [tuple(round(v, 4) for v in p) for p in points]
    unique_points = list(dict.fromkeys(sorted(rounded, key=lambda p: (-p[1], p[0]))))
    with open(filepath, "w") as f:
        f.write("#\n")
        for x, y in unique_points:
            f.write(f"{x:.4f} {y:.4f}\n")
        f.write("#\n")

def calculate_hv(filepath, ref_point, gen_number=None):
    cmd = ["../../material/hv-1.3-src/hv", "-r", f"{ref_point[0]} {ref_point[1]}", filepath]
    print("Ejecutando:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        hv = float(result.stdout.strip())
        if gen_number:
            print(f"Hipervolumen calculado para generación {gen_number}: {hv}")
        else:
            print("Hipervolumen calculado:", hv)
        return hv
    except ValueError:
        print("Error al interpretar la salida:", result.stdout)
        return 0.0

def calcular_referencia_global(files):
    all_points = []
    for file in files:
        with open(file) as f:
            lines = [line for line in f if line.strip() and not line.startswith("#")]
            pts = [list(map(float, line.split()[:2])) for line in lines]
            all_points.extend(pts)
    max_x = max(p[0] for p in all_points)
    max_y = max(p[1] for p in all_points)
    ref_x = max_x + abs(max_x) * 0.001
    ref_y = max_y + abs(max_y) * 0.001
    if ref_x == 0:
        ref_x = 0.1
    print(f"Punto de referencia global: ({ref_x}, {ref_y})")
    return (ref_x, ref_y)

@app.route("/run", methods=["POST"])
def run():
    instancia = request.json["instancia"]
    semilla = request.json["semilla"]
    num_var = request.json["num_var"]

    full_path = os.path.join("INSTANCES", instancia)
    subprocess.run(["./MOEAD", full_path, str(semilla), str(num_var)])

    base_name = parse_instance_name(instancia)
    files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    hv_results = []

    folder_path = f"FrentesDePareto/{base_name}"
    os.makedirs(folder_path, exist_ok=True)

    ref_point = calcular_referencia_global(files)
    resumen_path = os.path.join(folder_path, f"{base_name}_HV_summary.txt")

    with open(resumen_path, "w") as resumen_file:
        resumen_file.write(f"{ref_point[0]} {ref_point[1]}\n")
        for i, file in enumerate(files):
            with open(file) as f:
                lines = [line for line in f if line.strip() and not line.startswith("#")]
                points = [list(map(float, line.split()[:2])) for line in lines]
                nondominated = get_non_dominated(points)
                output_file = os.path.join(folder_path, f"{base_name}_GEN{i+1}.dat")

                if not nondominated:
                    hv_results.append(0.0)
                    resumen_file.write(f"GEN{i+1} 0.0\n")
                    continue

                save_front_to_file(nondominated, output_file)
                hv = calculate_hv(output_file, ref_point, gen_number=i+1)
                hv = hv if hv is not None else 0.0
                hv_results.append(hv)
                resumen_file.write(f"GEN{i+1} {hv:.4f}\n")
        resumen_file.write("#\n")

    return jsonify({"files": files, "hv": hv_results})

@app.route("/load", methods=["POST"])
def load():
    instancia = request.json["instancia"]
    recalcular = request.json.get("recalcular", True)
    base_name = parse_instance_name(instancia)

    files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    subfolder = os.path.join("FrentesDePareto", base_name)
    resumen_path = os.path.join(subfolder, f"{base_name}_HV_summary.txt")
    hv_results = []

    if not recalcular and os.path.exists(resumen_path):
        with open(resumen_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            if len(lines) > 1:
                hv_results = [float(line.split()[1]) for line in lines[1:]]
    else:
        ref_point = calcular_referencia_global(files)
        for i, file in enumerate(files):
            output_file = os.path.join(subfolder, f"{base_name}_GEN{i+1}.dat")
            if not os.path.exists(output_file):
                with open(file) as f:
                    lines = [line for line in f if line.strip() and not line.startswith("#")]
                    points = [list(map(float, line.split()[:2])) for line in lines]
                    nondominated = get_non_dominated(points)
                    if not nondominated:
                        hv_results.append(0.0)
                        continue
                    save_front_to_file(nondominated, output_file)
            with open(output_file) as f:
                lines = [line for line in f if line.strip() and not line.startswith("#")]
                points = [list(map(float, line.split()[:2])) for line in lines]
                hv = calculate_hv(output_file, ref_point, gen_number=i+1)
                hv_results.append(hv)

        # Guardar el nuevo resumen
        with open(resumen_path, "w") as f:
            f.write(f"{ref_point[0]:.3f} {ref_point[1]:.3f}\n")
            for i, hv in enumerate(hv_results):
                f.write(f"GEN{i+1} {hv:.4f}\n")
            f.write("#\n")

    return jsonify({"files": files, "hv": hv_results})

@app.route("/get/<path:filename>")
def get_file(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

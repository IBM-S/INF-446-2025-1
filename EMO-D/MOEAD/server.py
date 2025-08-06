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
    points_ordered = sorted(rounded, key=lambda p: -p[1])  # ordenar por f2 descendente
    unique_points = list(dict.fromkeys((tuple(p) for p in points_ordered)))
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
        return None

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
    print(f"Punto de referencia global: ({ref_x}, {ref_y})")
    return (ref_x, ref_y)

@app.route("/run", methods=["POST"])
def run():
    instancia = request.json["instancia"]
    semilla = request.json["semilla"]
    num_var = request.json["num_var"]

    subprocess.run(["./MOEAD", os.path.join("INSTANCES", instancia), str(semilla), str(num_var)])

    base_name = parse_instance_name(instancia)
    files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    hv_results = []

    os.makedirs("FrentesDePareto", exist_ok=True)
    ref_point = calcular_referencia_global(files)

    for i, file in enumerate(files):
        with open(file) as f:
            lines = [line for line in f if line.strip() and not line.startswith("#")]
            points = [list(map(float, line.split()[:2])) for line in lines]
            nondominated = get_non_dominated(points)
            if not nondominated:
                hv_results.append(None)
                continue

            output_file = f"FrentesDePareto/{base_name}_GEN{i+1}.dat"
            save_front_to_file(nondominated, output_file)

            hv = calculate_hv(output_file, ref_point, gen_number=i+1)
            hv_results.append(hv)

    return jsonify({"files": files, "hv": hv_results})

@app.route("/load", methods=["POST"])
def load():
    instancia = request.json["instancia"]
    base_name = parse_instance_name(instancia)
    files = sorted(glob.glob(f"SAVING/MOEAD/POF/POF_{instancia}_GEN_*.dat"))
    hv_results = []

    os.makedirs("FrentesDePareto", exist_ok=True)
    ref_point = calcular_referencia_global(files)

    for i, file in enumerate(files):
        output_file = f"FrentesDePareto/{base_name}_GEN{i+1}.dat"
        if not os.path.exists(output_file):
            with open(file) as f:
                lines = [line for line in f if line.strip() and not line.startswith("#")]
                points = [list(map(float, line.split()[:2])) for line in lines]
                nondominated = get_non_dominated(points)
                if not nondominated:
                    hv_results.append(None)
                    continue

                save_front_to_file(nondominated, output_file)
                hv = calculate_hv(output_file, ref_point, gen_number=i+1)
                hv_results.append(hv)
        else:
            # si ya existe, recalcular por consistencia
            with open(output_file) as f:
                lines = [line for line in f if line.strip() and not line.startswith("#")]
                points = [list(map(float, line.split()[:2])) for line in lines]
                hv = calculate_hv(output_file, ref_point, gen_number=i+1)
                hv_results.append(hv)

    return jsonify({"files": files, "hv": hv_results})

@app.route("/get/<path:filename>")
def get_file(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

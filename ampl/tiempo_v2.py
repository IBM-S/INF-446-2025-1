import os
import time
start = time.time()

os.system("../../../../../AMPL/ampl.exe mo_drp_location.run")

# os.system("../../../../../AMPL/ampl.exe DRP.run")

# os.system("../../../../../AMPL/ampl.exe mo_drp_relocation_simple.run")

end = time.time()
print("Tiempo real de ejecución:", end - start)

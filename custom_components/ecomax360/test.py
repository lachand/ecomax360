from .communication import Communication

comm = Communication()
data = comm.listenFrame("GET_DATAS")
print("Données reçues :", data)

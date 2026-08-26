import joblib
import numpy as np


CAMINHO_MODELO = "app/modelo_anomalia.joblib"


print("")
print("==============================")
print("TESTE DE INFERÊNCIA DA IA")
print("==============================")


# Carrega o modelo treinado
modelo = joblib.load(CAMINHO_MODELO)

print("Modelo carregado com sucesso.")


# Exemplo dentro do padrão utilizado no treinamento
evento_normal = np.array([
    [1, 120, 14]
])


# Exemplo propositalmente fora do domínio esperado
# Serve apenas para validar a capacidade de detecção do modelo
evento_atipico = np.array([
    [9, 10000, 100]
])


resultado_normal = modelo.predict(evento_normal)[0]
resultado_atipico = modelo.predict(evento_atipico)[0]


print("")
print("Amostra 1:")
print("Faixa: 1")
print("Intervalo: 120")
print("Hora decimal: 14")
print(
    "Resultado:",
    "NORMAL" if resultado_normal == 1 else "ANOMALIA"
)


print("")
print("Amostra 2:")
print("Entrada artificial fora do domínio esperado")
print(
    "Resultado:",
    "NORMAL" if resultado_atipico == 1 else "ANOMALIA"
)


print("")
print("==============================")
print("TESTE FINALIZADO")
print("==============================")
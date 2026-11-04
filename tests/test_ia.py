import os
import unittest


os.environ["TEMPO_DUPLICIDADE"] = "30"

from app import anomaly  # noqa: E402
from app.config import TEMPO_DUPLICIDADE  # noqa: E402


class ModuloInteligenciaArtificialTest(unittest.TestCase):
    def test_configuracao_reduz_janela_para_30_segundos(self):
        self.assertEqual(TEMPO_DUPLICIDADE, 30)

    def test_evento_normal_e_liberado_para_cobranca(self):
        resultado = anomaly.classificar_com_ia(120)
        self.assertIsNone(resultado["classificacao"])
        self.assertIsNone(resultado["predicao_duplicidade"])
        self.assertIsNone(resultado["score_duplicidade"])
        self.assertEqual(resultado["origem_classificacao"], "fora_janela")

    def test_modelo_temporal_nao_emite_anomalia_comportamental(self):
        resultado = anomaly.classificar_com_ia(120)
        self.assertIsNone(resultado["classificacao"])
        self.assertEqual(resultado["origem_classificacao"], "fora_janela")

    def test_repeticao_em_10_segundos_e_duplicidade(self):
        resultado = anomaly.classificar_com_ia(10)
        self.assertEqual(resultado["predicao_duplicidade"], -1)
        self.assertEqual(resultado["origem_classificacao"], "ia_temporal")
        self.assertEqual(resultado["classificacao"], "duplicidade")

    def test_repeticao_em_29_segundos_e_duplicidade(self):
        resultado = anomaly.classificar_com_ia(29)
        self.assertEqual(resultado["predicao_duplicidade"], -1)
        self.assertEqual(resultado["origem_classificacao"], "ia_temporal")
        self.assertEqual(resultado["classificacao"], "duplicidade")

    def test_limite_de_30_segundos_nao_e_regra_de_duplicidade(self):
        resultado = anomaly.classificar_com_ia(30)
        self.assertIsNone(resultado["classificacao"])
        self.assertIsNone(resultado["predicao_duplicidade"])
        self.assertEqual(resultado["origem_classificacao"], "fora_janela")


if __name__ == "__main__":
    unittest.main()

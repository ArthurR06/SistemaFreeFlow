import os
import unittest


os.environ["TEMPO_DUPLICIDADE"] = "30"

from app import anomaly  # noqa: E402
from app.config import TEMPO_DUPLICIDADE  # noqa: E402


class ModuloInteligenciaArtificialTest(unittest.TestCase):
    def test_configuracao_reduz_janela_para_30_segundos(self):
        self.assertEqual(TEMPO_DUPLICIDADE, 30)

    def test_evento_normal_e_liberado_para_cobranca(self):
        resultado = anomaly.classificar_com_ia(1, 120, 14)
        self.assertEqual(resultado["predicao"], 1)
        self.assertIsNone(resultado["classificacao"])
        self.assertGreaterEqual(resultado["score"], 0)

    def test_repeticao_em_10_segundos_e_duplicidade(self):
        resultado = anomaly.classificar_com_ia(1, 10, 14)
        self.assertEqual(resultado["predicao_duplicidade"], -1)
        self.assertEqual(resultado["origem_classificacao"], "ia_temporal")
        self.assertEqual(resultado["classificacao"], "duplicidade")

    def test_repeticao_em_29_segundos_e_duplicidade(self):
        resultado = anomaly.classificar_com_ia(2, 29, 12)
        self.assertEqual(resultado["predicao_duplicidade"], -1)
        self.assertEqual(resultado["origem_classificacao"], "ia_temporal")
        self.assertEqual(resultado["classificacao"], "duplicidade")

    def test_limite_de_30_segundos_nao_e_regra_de_duplicidade(self):
        resultado = anomaly.classificar_com_ia(1, 30, 14)
        self.assertNotEqual(resultado["classificacao"], "duplicidade")

    def test_ia_bloqueia_anomalia_fora_da_janela_de_duplicidade(self):
        resultado = anomaly.classificar_com_ia(2, 120, 2)
        self.assertEqual(resultado["predicao"], -1)
        self.assertEqual(resultado["classificacao"], "ia_anomalia")
        self.assertLess(resultado["score"], 0)


if __name__ == "__main__":
    unittest.main()

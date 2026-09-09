from tools import calculate, convert_units, element_info, run_tool


class TestCalculateCorrect:
    def test_aritmetica_basica(self):
        assert calculate("2 + 3 * 4") == "14"

    def test_potencia_e_decimal(self):
        # exatamente o caso da parábola: y = 2x² + 5x + 3 com x = -1.25
        assert calculate("2*(-1.25)**2 + 5*(-1.25) + 3") == "-0.125"

    def test_raiz(self):
        assert calculate("sqrt(64)") == "8"

    def test_circunflexo_como_potencia(self):
        assert calculate("2^10") == "1024"

    def test_funcoes_e_constantes(self):
        assert calculate("log10(1000)") == "3"
        assert calculate("cos(0)") == "1"

    def test_divisao_por_zero(self):
        assert "zero" in calculate("1/0").lower()


class TestCalculateSafe:
    """A calculadora NUNCA pode executar código arbitrário."""

    def test_bloqueia_import(self):
        assert calculate("__import__('os')").startswith("Erro")

    def test_bloqueia_nome_arbitrario(self):
        assert calculate("open('/etc/passwd')").startswith("Erro")

    def test_bloqueia_atributo(self):
        assert calculate("(1).__class__").startswith("Erro")

    def test_bloqueia_funcao_nao_listada(self):
        assert calculate("eval('1+1')").startswith("Erro")


class TestConvertUnits:
    def test_gramas_para_quilogramas(self):
        assert convert_units(800, "g", "kg") == "0.8"

    def test_km_h_para_m_s(self):
        result = float(convert_units(36, "km/h", "m/s"))
        assert abs(result - 10.0) < 1e-6

    def test_celsius_para_kelvin(self):
        assert convert_units(100, "°C", "K") == "373.15"

    def test_kelvin_para_celsius(self):
        assert convert_units(0, "K", "°C") == "-273.15"

    def test_celsius_para_fahrenheit(self):
        assert convert_units(0, "°C", "°F") == "32"

    def test_metros_para_cm(self):
        assert convert_units(1, "m", "cm") == "100"

    def test_atm_para_pa(self):
        result = float(convert_units(1, "atm", "Pa"))
        assert abs(result - 101325) < 1

    def test_grandeza_errada(self):
        result = convert_units(1, "kg", "m")
        assert result.startswith("Erro")

    def test_unidade_desconhecida(self):
        result = convert_units(1, "xyz", "kg")
        assert result.startswith("Erro")

    def test_joule_para_cal(self):
        result = float(convert_units(4.184, "J", "cal"))
        assert abs(result - 1.0) < 1e-6

    def test_graus_para_rad(self):
        import math
        result = float(convert_units(180, "graus", "rad"))
        assert abs(result - math.pi) < 1e-9


class TestElementInfo:
    def test_por_simbolo(self):
        result = element_info("Fe")
        assert "Ferro" in result
        assert "26" in result
        assert "55.845" in result

    def test_por_nome(self):
        result = element_info("oxigênio")
        assert "O" in result
        assert "8" in result

    def test_por_nome_sem_acento(self):
        result = element_info("oxigenio")
        assert "Oxigênio" in result

    def test_por_numero(self):
        result = element_info("1")
        assert "Hidrogênio" in result

    def test_elemento_inexistente(self):
        result = element_info("Xx")
        assert result.startswith("Erro")

    def test_categoria_gas_nobre(self):
        result = element_info("He")
        assert "gás-nobre" in result

    def test_halogênio(self):
        result = element_info("Cl")
        assert "halogênio" in result

    def test_lantanideo(self):
        result = element_info("Ce")
        assert "lantanídeo" in result


class TestRunTool:
    def test_dispatch_calcular(self):
        assert run_tool("calcular", {"expressao": "10 / 4"}) == "2.5"

    def test_dispatch_converter(self):
        assert run_tool("converter", {"valor": 1000, "de": "g", "para": "kg"}) == "1"

    def test_dispatch_elemento(self):
        result = run_tool("elemento", {"busca": "Au"})
        assert "Ouro" in result

    def test_ferramenta_desconhecida(self):
        assert run_tool("inexistente", {}).startswith("Erro")

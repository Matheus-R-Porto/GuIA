"""
tools.py — Ferramentas que o modelo pode chamar (function calling / tool-use).

Ferramentas disponíveis:
  calcular        — aritmética determinística via AST (sem eval)
  converter       — conversão de unidades (física, química)
  elemento        — tabela periódica (símbolo, massa atômica, número atômico...)
"""
import ast
import math
import operator
import re

# ---------------------------------------------------------------------------
# CALCULADORA
# ---------------------------------------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_ALLOWED_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}

_ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "log": math.log, "log10": math.log10, "log2": math.log2, "ln": math.log,
    "exp": math.exp, "abs": abs, "fabs": math.fabs,
    "factorial": math.factorial, "gcd": math.gcd,
    "floor": math.floor, "ceil": math.ceil, "round": round,
    "degrees": math.degrees, "radians": math.radians,
    "hypot": math.hypot, "pow": math.pow, "min": min, "max": max,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("apenas valores numéricos são permitidos")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError("operador não permitido")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError("operador unário não permitido")
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("chamada inválida")
        fn = _ALLOWED_FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"função não permitida: {node.func.id}")
        return fn(*[_eval_node(a) for a in node.args])
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[node.id]
        raise ValueError(f"nome não permitido: {node.id}")
    raise ValueError("expressão não permitida")


def calculate(expression: str) -> str:
    """Avalia uma expressão matemática com segurança. Retorna o resultado como texto."""
    expr = expression.strip().replace("^", "**")
    if not expr:
        return "Erro: expressão vazia"
    # Vírgula decimal PT-BR → ponto. Só converte vírgula entre dígitos SEM espaço
    # (ex.: "0,093" → "0.093"); argumentos de função usam vírgula com espaço
    # ("log(8, 2)"), que ficam intactos.
    expr = re.sub(r"(?<=\d),(?=\d)", ".", expr)
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval_node(tree)
    except ZeroDivisionError:
        return "Erro: divisão por zero"
    except Exception as e:
        return f"Erro: {e}"
    if isinstance(result, float):
        if result.is_integer():
            return str(int(result))
        result = round(result, 10)
    return str(result)


CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calcular",
        "description": (
            "Avalia expressão matemática com precisão. Use SEMPRE que houver cálculo numérico — "
            "nunca calcule de cabeça. Suporta +,-,*,/,**,sqrt,sin,cos,tan,log,ln,exp,factorial,pi,e. "
            "Use ponto decimal. Ex: '2*(-1.25)**2 + 5*(-1.25) + 3'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expressao": {
                    "type": "string",
                    "description": "Expressão a calcular. Ex: '2*(-1.25)**2 + 5*(-1.25) + 3' ou 'sqrt(64)'",
                }
            },
            "required": ["expressao"],
        },
    },
}

# ---------------------------------------------------------------------------
# CONVERSOR DE UNIDADES
# ---------------------------------------------------------------------------

# Todas as unidades mapeadas para a unidade-base SI de cada categoria.
# Temperatura é tratada separadamente (não é conversão linear simples).
_UNITS: dict[str, dict[str, float]] = {
    # Comprimento → metro (m)
    "comprimento": {
        "m": 1, "metro": 1, "metros": 1,
        "km": 1e3, "quilômetro": 1e3, "quilometro": 1e3, "quilômetros": 1e3, "quilometros": 1e3,
        "cm": 1e-2, "centímetro": 1e-2, "centimetro": 1e-2, "centímetros": 1e-2, "centimetros": 1e-2,
        "mm": 1e-3, "milímetro": 1e-3, "milimetro": 1e-3, "milímetros": 1e-3, "milimetros": 1e-3,
        "µm": 1e-6, "um": 1e-6, "micrômetro": 1e-6, "micrometro": 1e-6,
        "nm": 1e-9, "nanômetro": 1e-9, "nanometro": 1e-9,
        "å": 1e-10, "angstrom": 1e-10, "ångström": 1e-10,
        "mi": 1609.344, "milha": 1609.344, "milhas": 1609.344,
        "ft": 0.3048, "pé": 0.3048, "pe": 0.3048, "pés": 0.3048, "pes": 0.3048,
        "in": 0.0254, "polegada": 0.0254, "polegadas": 0.0254,
        "yd": 0.9144, "jarda": 0.9144, "jardas": 0.9144,
        "ly": 9.461e15, "ano-luz": 9.461e15,
    },
    # Massa → quilograma (kg)
    "massa": {
        "kg": 1, "quilograma": 1, "quilogramas": 1,
        "g": 1e-3, "grama": 1e-3, "gramas": 1e-3,
        "mg": 1e-6, "miligrama": 1e-6, "miligramas": 1e-6,
        "µg": 1e-9, "ug": 1e-9, "micrograma": 1e-9, "microgramas": 1e-9,
        "t": 1e3, "tonelada": 1e3, "toneladas": 1e3,
        "lb": 0.453592, "libra": 0.453592, "libras": 0.453592,
        "oz": 0.0283495, "onça": 0.0283495, "onca": 0.0283495,
        "u": 1.66054e-27, "uma": 1.66054e-27, "dalton": 1.66054e-27,
    },
    # Tempo → segundo (s)
    "tempo": {
        "s": 1, "segundo": 1, "segundos": 1,
        "ms": 1e-3, "milissegundo": 1e-3, "milissegundos": 1e-3,
        "µs": 1e-6, "us": 1e-6, "microssegundo": 1e-6,
        "ns": 1e-9, "nanossegundo": 1e-9,
        "min": 60, "minuto": 60, "minutos": 60,
        "h": 3600, "hora": 3600, "horas": 3600,
        "d": 86400, "dia": 86400, "dias": 86400,
        "semana": 604800, "semanas": 604800,
        "ano": 31557600, "anos": 31557600,
    },
    # Área → m²
    "area": {
        "m2": 1, "m²": 1,
        "km2": 1e6, "km²": 1e6,
        "cm2": 1e-4, "cm²": 1e-4,
        "mm2": 1e-6, "mm²": 1e-6,
        "ha": 1e4, "hectare": 1e4, "hectares": 1e4,
        "ft2": 0.092903, "ft²": 0.092903,
        "in2": 6.4516e-4, "in²": 6.4516e-4,
        "mi2": 2.59e6, "mi²": 2.59e6,
    },
    # Volume → m³ (mas também litros)
    "volume": {
        "m3": 1, "m³": 1,
        "l": 1e-3, "litro": 1e-3, "litros": 1e-3,
        "ml": 1e-6, "mililitro": 1e-6, "mililitros": 1e-6,
        "cl": 1e-5, "centilitro": 1e-5,
        "dl": 1e-4, "decilitro": 1e-4,
        "cm3": 1e-6, "cm³": 1e-6,
        "mm3": 1e-9, "mm³": 1e-9,
        "ft3": 0.0283168, "ft³": 0.0283168,
        "in3": 1.63871e-5, "in³": 1.63871e-5,
        "gallon": 3.78541e-3, "galão": 3.78541e-3, "galao": 3.78541e-3,
    },
    # Velocidade → m/s
    "velocidade": {
        "m/s": 1,
        "km/h": 1 / 3.6, "kmh": 1 / 3.6, "km/hora": 1 / 3.6,
        "mph": 0.44704, "mi/h": 0.44704,
        "ft/s": 0.3048,
        "nó": 0.514444, "no": 0.514444, "knot": 0.514444,
        "mach": 343,
    },
    # Energia → joule (J)
    "energia": {
        "j": 1, "joule": 1, "joules": 1,
        "kj": 1e3, "quilojoule": 1e3, "kilojoule": 1e3,
        "mj": 1e6, "megajoule": 1e6,
        "cal": 4.184, "caloria": 4.184, "calorias": 4.184,
        "kcal": 4184, "quilocaloria": 4184, "caloria alimentar": 4184,
        "wh": 3600, "watt-hora": 3600,
        "kwh": 3.6e6, "quilowatt-hora": 3.6e6,
        "ev": 1.602176634e-19, "elétron-volt": 1.602176634e-19, "eletron-volt": 1.602176634e-19,
        "erg": 1e-7,
    },
    # Pressão → pascal (Pa)
    "pressao": {
        "pa": 1, "pascal": 1,
        "kpa": 1e3, "quilopascal": 1e3,
        "mpa": 1e6, "megapascal": 1e6,
        "atm": 101325, "atmosfera": 101325,
        "bar": 1e5,
        "mbar": 100, "milibar": 100,
        "mmhg": 133.322, "torr": 133.322,
        "psi": 6894.76,
    },
    # Força → newton (N)
    "forca": {
        "n": 1, "newton": 1,
        "kn": 1e3, "quilonewton": 1e3,
        "mn": 1e6, "meganewton": 1e6,
        "kgf": 9.80665, "quilograma-força": 9.80665,
        "lbf": 4.44822,
        "dyn": 1e-5, "dina": 1e-5,
    },
    # Potência → watt (W)
    "potencia": {
        "w": 1, "watt": 1,
        "kw": 1e3, "quilowatt": 1e3,
        "mw": 1e6, "megawatt": 1e6,
        "gw": 1e9, "gigawatt": 1e9,
        "hp": 745.7, "cv": 735.499,
    },
    # Ângulo → radiano (rad)
    "angulo": {
        "rad": 1, "radiano": 1, "radianos": 1,
        "deg": math.pi / 180, "grau": math.pi / 180, "graus": math.pi / 180, "°": math.pi / 180,
        "grad": math.pi / 200, "gradiano": math.pi / 200,
        "rev": 2 * math.pi, "volta": 2 * math.pi,
    },
}

# Índice reverso: unidade → categoria
_UNIT_TO_CATEGORY: dict[str, str] = {}
for _cat, _units in _UNITS.items():
    for _u in _units:
        _UNIT_TO_CATEGORY[_u] = _cat

# Temperatura tem lógica especial (offset + escala)
_TEMP_UNITS = {"°c", "c", "celsius", "k", "kelvin", "°f", "f", "fahrenheit"}


def _to_celsius(valor: float, unidade: str) -> float:
    u = unidade.lower().strip()
    if u in ("°c", "c", "celsius"):
        return valor
    if u in ("k", "kelvin"):
        return valor - 273.15
    if u in ("°f", "f", "fahrenheit"):
        return (valor - 32) * 5 / 9
    raise ValueError(f"Unidade de temperatura desconhecida: '{unidade}'")


def _from_celsius(valor: float, unidade: str) -> float:
    u = unidade.lower().strip()
    if u in ("°c", "c", "celsius"):
        return valor
    if u in ("k", "kelvin"):
        return valor + 273.15
    if u in ("°f", "f", "fahrenheit"):
        return valor * 9 / 5 + 32
    raise ValueError(f"Unidade de temperatura desconhecida: '{unidade}'")


def convert_units(valor: float, de: str, para: str) -> str:
    """Converte valor da unidade 'de' para 'para'. Retorna resultado como texto."""
    de_l = de.lower().strip()
    para_l = para.lower().strip()

    # Temperatura
    if de_l in _TEMP_UNITS or para_l in _TEMP_UNITS:
        try:
            resultado = _from_celsius(_to_celsius(valor, de_l), para_l)
        except ValueError as exc:
            return f"Erro: {exc}"
        resultado = round(resultado, 6)
        if isinstance(resultado, float) and resultado == int(resultado):
            return str(int(resultado))
        return str(resultado)

    # Demais unidades
    cat_de = _UNIT_TO_CATEGORY.get(de_l)
    cat_para = _UNIT_TO_CATEGORY.get(para_l)

    if cat_de is None:
        return f"Erro: unidade desconhecida '{de}'"
    if cat_para is None:
        return f"Erro: unidade desconhecida '{para}'"
    if cat_de != cat_para:
        return f"Erro: '{de}' e '{para}' são grandezas diferentes ({cat_de} vs {cat_para})"

    fator_de = _UNITS[cat_de][de_l]
    fator_para = _UNITS[cat_para][para_l]
    resultado = valor * fator_de / fator_para

    if isinstance(resultado, float):
        if resultado == int(resultado):
            return str(int(resultado))
        resultado = round(resultado, 10)
    return str(resultado)


CONVERTER_TOOL = {
    "type": "function",
    "function": {
        "name": "converter",
        "description": (
            "Converte valores entre unidades físicas. Use para verificar conversões do aluno. "
            "Suporta: comprimento, massa, tempo, temperatura, área, volume, velocidade, energia, pressão, força, ângulo. "
            "Ex: 800 g→kg, 45 km/h→m/s, 100 °C→K."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "valor": {"type": "number", "description": "Valor numérico a converter"},
                "de": {"type": "string", "description": "Unidade de origem (ex: 'g', 'km/h', '°C')"},
                "para": {"type": "string", "description": "Unidade de destino (ex: 'kg', 'm/s', 'K')"},
            },
            "required": ["valor", "de", "para"],
        },
    },
}

# ---------------------------------------------------------------------------
# TABELA PERIÓDICA
# ---------------------------------------------------------------------------
# Campos: (símbolo, nome_pt, numero_atomico, massa_atomica, grupo, periodo, categoria)
# categoria: metal-alcalino, metal-alcalino-terroso, metal-de-transição, metal-pós-transição,
#            semimetal, não-metal, halogênio, gás-nobre, lantanídeo, actinídeo
_ELEMENTS: list[tuple] = [
    ("H",  "Hidrogênio",    1,   1.008,    1,  1, "não-metal"),
    ("He", "Hélio",         2,   4.0026,  18,  1, "gás-nobre"),
    ("Li", "Lítio",         3,   6.94,     1,  2, "metal-alcalino"),
    ("Be", "Berílio",       4,   9.0122,   2,  2, "metal-alcalino-terroso"),
    ("B",  "Boro",          5,  10.81,    13,  2, "semimetal"),
    ("C",  "Carbono",       6,  12.011,   14,  2, "não-metal"),
    ("N",  "Nitrogênio",    7,  14.007,   15,  2, "não-metal"),
    ("O",  "Oxigênio",      8,  15.999,   16,  2, "não-metal"),
    ("F",  "Flúor",         9,  18.998,   17,  2, "halogênio"),
    ("Ne", "Neônio",       10,  20.180,   18,  2, "gás-nobre"),
    ("Na", "Sódio",        11,  22.990,    1,  3, "metal-alcalino"),
    ("Mg", "Magnésio",     12,  24.305,    2,  3, "metal-alcalino-terroso"),
    ("Al", "Alumínio",     13,  26.982,   13,  3, "metal-pós-transição"),
    ("Si", "Silício",      14,  28.085,   14,  3, "semimetal"),
    ("P",  "Fósforo",      15,  30.974,   15,  3, "não-metal"),
    ("S",  "Enxofre",      16,  32.06,    16,  3, "não-metal"),
    ("Cl", "Cloro",        17,  35.45,    17,  3, "halogênio"),
    ("Ar", "Argônio",      18,  39.948,   18,  3, "gás-nobre"),
    ("K",  "Potássio",     19,  39.098,    1,  4, "metal-alcalino"),
    ("Ca", "Cálcio",       20,  40.078,    2,  4, "metal-alcalino-terroso"),
    ("Sc", "Escândio",     21,  44.956,    3,  4, "metal-de-transição"),
    ("Ti", "Titânio",      22,  47.867,    4,  4, "metal-de-transição"),
    ("V",  "Vanádio",      23,  50.942,    5,  4, "metal-de-transição"),
    ("Cr", "Cromo",        24,  51.996,    6,  4, "metal-de-transição"),
    ("Mn", "Manganês",     25,  54.938,    7,  4, "metal-de-transição"),
    ("Fe", "Ferro",        26,  55.845,    8,  4, "metal-de-transição"),
    ("Co", "Cobalto",      27,  58.933,    9,  4, "metal-de-transição"),
    ("Ni", "Níquel",       28,  58.693,   10,  4, "metal-de-transição"),
    ("Cu", "Cobre",        29,  63.546,   11,  4, "metal-de-transição"),
    ("Zn", "Zinco",        30,  65.38,    12,  4, "metal-de-transição"),
    ("Ga", "Gálio",        31,  69.723,   13,  4, "metal-pós-transição"),
    ("Ge", "Germânio",     32,  72.630,   14,  4, "semimetal"),
    ("As", "Arsênio",      33,  74.922,   15,  4, "semimetal"),
    ("Se", "Selênio",      34,  78.971,   16,  4, "não-metal"),
    ("Br", "Bromo",        35,  79.904,   17,  4, "halogênio"),
    ("Kr", "Criptônio",    36,  83.798,   18,  4, "gás-nobre"),
    ("Rb", "Rubídio",      37,  85.468,    1,  5, "metal-alcalino"),
    ("Sr", "Estrôncio",    38,  87.62,     2,  5, "metal-alcalino-terroso"),
    ("Y",  "Ítrio",        39,  88.906,    3,  5, "metal-de-transição"),
    ("Zr", "Zircônio",     40,  91.224,    4,  5, "metal-de-transição"),
    ("Nb", "Nióbio",       41,  92.906,    5,  5, "metal-de-transição"),
    ("Mo", "Molibdênio",   42,  95.95,     6,  5, "metal-de-transição"),
    ("Tc", "Tecnécio",     43,  97.0,      7,  5, "metal-de-transição"),
    ("Ru", "Rutênio",      44, 101.07,     8,  5, "metal-de-transição"),
    ("Rh", "Ródio",        45, 102.906,    9,  5, "metal-de-transição"),
    ("Pd", "Paládio",      46, 106.42,    10,  5, "metal-de-transição"),
    ("Ag", "Prata",        47, 107.868,   11,  5, "metal-de-transição"),
    ("Cd", "Cádmio",       48, 112.414,   12,  5, "metal-de-transição"),
    ("In", "Índio",        49, 114.818,   13,  5, "metal-pós-transição"),
    ("Sn", "Estanho",      50, 118.710,   14,  5, "metal-pós-transição"),
    ("Sb", "Antimônio",    51, 121.760,   15,  5, "semimetal"),
    ("Te", "Telúrio",      52, 127.60,    16,  5, "semimetal"),
    ("I",  "Iodo",         53, 126.904,   17,  5, "halogênio"),
    ("Xe", "Xenônio",      54, 131.293,   18,  5, "gás-nobre"),
    ("Cs", "Césio",        55, 132.905,    1,  6, "metal-alcalino"),
    ("Ba", "Bário",        56, 137.327,    2,  6, "metal-alcalino-terroso"),
    ("La", "Lantânio",     57, 138.905,    3,  6, "lantanídeo"),
    ("Ce", "Cério",        58, 140.116,    None, 6, "lantanídeo"),
    ("Pr", "Praseodímio",  59, 140.908,   None, 6, "lantanídeo"),
    ("Nd", "Neodímio",     60, 144.242,   None, 6, "lantanídeo"),
    ("Pm", "Promécio",     61, 145.0,     None, 6, "lantanídeo"),
    ("Sm", "Samário",      62, 150.36,    None, 6, "lantanídeo"),
    ("Eu", "Európio",      63, 151.964,   None, 6, "lantanídeo"),
    ("Gd", "Gadolínio",    64, 157.25,    None, 6, "lantanídeo"),
    ("Tb", "Térbio",       65, 158.925,   None, 6, "lantanídeo"),
    ("Dy", "Disprósio",    66, 162.500,   None, 6, "lantanídeo"),
    ("Ho", "Hólmio",       67, 164.930,   None, 6, "lantanídeo"),
    ("Er", "Érbio",        68, 167.259,   None, 6, "lantanídeo"),
    ("Tm", "Túlio",        69, 168.934,   None, 6, "lantanídeo"),
    ("Yb", "Itérbio",      70, 173.045,   None, 6, "lantanídeo"),
    ("Lu", "Lutécio",      71, 174.967,   14, 6, "lantanídeo"),
    ("Hf", "Háfnio",       72, 178.49,     4,  6, "metal-de-transição"),
    ("Ta", "Tântalo",      73, 180.948,    5,  6, "metal-de-transição"),
    ("W",  "Tungstênio",   74, 183.84,     6,  6, "metal-de-transição"),
    ("Re", "Rênio",        75, 186.207,    7,  6, "metal-de-transição"),
    ("Os", "Ósmio",        76, 190.23,     8,  6, "metal-de-transição"),
    ("Ir", "Irídio",       77, 192.217,    9,  6, "metal-de-transição"),
    ("Pt", "Platina",      78, 195.084,   10,  6, "metal-de-transição"),
    ("Au", "Ouro",         79, 196.967,   11,  6, "metal-de-transição"),
    ("Hg", "Mercúrio",     80, 200.592,   12,  6, "metal-de-transição"),
    ("Tl", "Tálio",        81, 204.38,    13,  6, "metal-pós-transição"),
    ("Pb", "Chumbo",       82, 207.2,     14,  6, "metal-pós-transição"),
    ("Bi", "Bismuto",      83, 208.980,   15,  6, "metal-pós-transição"),
    ("Po", "Polônio",      84, 209.0,     16,  6, "semimetal"),
    ("At", "Astato",       85, 210.0,     17,  6, "halogênio"),
    ("Rn", "Radônio",      86, 222.0,     18,  6, "gás-nobre"),
    ("Fr", "Frâncio",      87, 223.0,      1,  7, "metal-alcalino"),
    ("Ra", "Rádio",        88, 226.0,      2,  7, "metal-alcalino-terroso"),
    ("Ac", "Actínio",      89, 227.0,      3,  7, "actinídeo"),
    ("Th", "Tório",        90, 232.038,   None, 7, "actinídeo"),
    ("Pa", "Protactínio",  91, 231.036,   None, 7, "actinídeo"),
    ("U",  "Urânio",       92, 238.029,   None, 7, "actinídeo"),
    ("Np", "Netúnio",      93, 237.0,     None, 7, "actinídeo"),
    ("Pu", "Plutônio",     94, 244.0,     None, 7, "actinídeo"),
    ("Am", "Amerício",     95, 243.0,     None, 7, "actinídeo"),
    ("Cm", "Cúrio",        96, 247.0,     None, 7, "actinídeo"),
    ("Bk", "Berquélio",    97, 247.0,     None, 7, "actinídeo"),
    ("Cf", "Califórnio",   98, 251.0,     None, 7, "actinídeo"),
    ("Es", "Einstênio",    99, 252.0,     None, 7, "actinídeo"),
    ("Fm", "Férmio",      100, 257.0,     None, 7, "actinídeo"),
    ("Md", "Mendelévio",  101, 258.0,     None, 7, "actinídeo"),
    ("No", "Nobélio",     102, 259.0,     None, 7, "actinídeo"),
    ("Lr", "Laurêncio",   103, 266.0,     14,  7, "actinídeo"),
    ("Rf", "Rutherfórdio",104, 267.0,      4,  7, "metal-de-transição"),
    ("Db", "Dúbnio",      105, 268.0,      5,  7, "metal-de-transição"),
    ("Sg", "Seabórgio",   106, 269.0,      6,  7, "metal-de-transição"),
    ("Bh", "Bóhrio",      107, 270.0,      7,  7, "metal-de-transição"),
    ("Hs", "Hássio",      108, 277.0,      8,  7, "metal-de-transição"),
    ("Mt", "Meitnério",   109, 278.0,      9,  7, "metal-de-transição"),
    ("Ds", "Darmstádio",  110, 281.0,     10,  7, "metal-de-transição"),
    ("Rg", "Roentgênio",  111, 282.0,     11,  7, "metal-de-transição"),
    ("Cn", "Copernício",  112, 285.0,     12,  7, "metal-de-transição"),
    ("Nh", "Nihônio",     113, 286.0,     13,  7, "metal-pós-transição"),
    ("Fl", "Fleróvio",    114, 289.0,     14,  7, "metal-pós-transição"),
    ("Mc", "Moscóvio",    115, 290.0,     15,  7, "metal-pós-transição"),
    ("Lv", "Livermório",  116, 293.0,     16,  7, "metal-pós-transição"),
    ("Ts", "Tenessino",   117, 294.0,     17,  7, "halogênio"),
    ("Og", "Oganessônio", 118, 294.0,     18,  7, "gás-nobre"),
]

# Índices para busca rápida
_BY_SYMBOL  = {e[0].lower(): e for e in _ELEMENTS}
_BY_NUMBER  = {e[2]: e for e in _ELEMENTS}
_BY_NAME    = {e[1].lower(): e for e in _ELEMENTS}
# alias sem acento
import unicodedata as _ud
_BY_NAME_NORM = {
    _ud.normalize("NFKD", e[1]).encode("ascii", "ignore").decode().lower(): e
    for e in _ELEMENTS
}


def element_info(busca: str) -> str:
    """Retorna dados do elemento por símbolo, nome ou número atômico."""
    b = busca.strip()

    # Busca por número atômico
    if b.isdigit():
        elem = _BY_NUMBER.get(int(b))
        if elem is None:
            return f"Erro: nenhum elemento com número atômico {b}"
    else:
        bl = b.lower()
        bl_norm = _ud.normalize("NFKD", bl).encode("ascii", "ignore").decode()
        elem = (
            _BY_SYMBOL.get(bl)
            or _BY_NAME.get(bl)
            or _BY_NAME_NORM.get(bl_norm)
        )
        if elem is None:
            return f"Erro: elemento '{busca}' não encontrado"

    sym, nome, z, massa, grupo, periodo, cat = elem
    grupo_str = str(grupo) if grupo is not None else "série f"
    return (
        f"{nome} ({sym}) | Z={z} | Massa atômica={massa} u | "
        f"Grupo={grupo_str} | Período={periodo} | {cat}"
    )


PERIODIC_TABLE_TOOL = {
    "type": "function",
    "function": {
        "name": "elemento",
        "description": (
            "Consulta tabela periódica por símbolo (ex: 'Fe'), nome (ex: 'ferro') ou número atômico (ex: '26'). "
            "Retorna: nome, Z, massa atômica, grupo, período e categoria."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "busca": {
                    "type": "string",
                    "description": "Símbolo (ex: 'Fe'), nome (ex: 'ferro') ou número atômico (ex: '26')",
                }
            },
            "required": ["busca"],
        },
    },
}

# ---------------------------------------------------------------------------
# LISTA DE FERRAMENTAS (exportada para o provider)
# ---------------------------------------------------------------------------
ALL_TOOLS = [CALCULATOR_TOOL, CONVERTER_TOOL, PERIODIC_TABLE_TOOL]


# ---------------------------------------------------------------------------
# DISPATCHER
# ---------------------------------------------------------------------------
def run_tool(name: str, arguments: dict) -> str:
    """Executa uma ferramenta pelo nome e retorna o resultado como texto."""
    if name == "calcular":
        return calculate(str(arguments.get("expressao", "")))
    if name == "converter":
        valor = arguments.get("valor")
        de = str(arguments.get("de", ""))
        para = str(arguments.get("para", ""))
        if valor is None:
            return "Erro: parâmetro 'valor' ausente"
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return f"Erro: 'valor' inválido: {valor!r}"
        return convert_units(valor, de, para)
    if name == "elemento":
        return element_info(str(arguments.get("busca", "")))
    return f"Erro: ferramenta desconhecida '{name}'"

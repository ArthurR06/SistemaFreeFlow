from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path(__file__).with_name("der-banco-atual.png")

WIDTH = 2480
HEIGHT = 3400

COLORS = {
    "background": "#F7FAFC",
    "surface": "#FFFFFF",
    "header": "#063B66",
    "header_alt": "#075985",
    "text": "#102A43",
    "muted": "#52667A",
    "border": "#A8C1D8",
    "row_alt": "#EEF5FA",
    "pk": "#E9A23B",
    "fk": "#2F80ED",
    "unique": "#208A68",
    "relation": "#245B85",
    "logical": "#8093A5",
    "note": "#EAF2F8",
}

FONT_REGULAR_PATH = "C:/Windows/Fonts/segoeui.ttf"
FONT_SEMIBOLD_PATH = "C:/Windows/Fonts/seguisb.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {
        "regular": FONT_REGULAR_PATH,
        "semibold": FONT_SEMIBOLD_PATH,
        "bold": FONT_BOLD_PATH,
    }[weight]
    return ImageFont.truetype(path, size)


TABLE_FONT = font(42, "bold")
ROW_FONT = font(30)
ROW_SEMIBOLD_FONT = font(30, "semibold")
LABEL_FONT = font(29, "semibold")
NOTE_FONT = font(28)
LEGEND_FONT = font(26)


image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["background"])
draw = ImageDraw.Draw(image)


def dashed_line(points, fill, width=5, dash=20, gap=14):
    for start, end in zip(points, points[1:]):
        x1, y1 = start
        x2, y2 = end
        dx, dy = x2 - x1, y2 - y1
        length = max(abs(dx), abs(dy))
        if length == 0:
            continue
        steps = max(1, int(length / (dash + gap)))
        for index in range(steps + 1):
            begin = index * (dash + gap) / length
            finish = min(begin + dash / length, 1)
            if begin > 1:
                break
            draw.line(
                (
                    x1 + dx * begin,
                    y1 + dy * begin,
                    x1 + dx * finish,
                    y1 + dy * finish,
                ),
                fill=fill,
                width=width,
            )


def relationship(points, left_label: str, right_label: str, label_positions):
    draw.line(points, fill=COLORS["relation"], width=7, joint="curve")
    radius = 9
    for x, y in (points[0], points[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=COLORS["relation"])
    for text, position in zip((left_label, right_label), label_positions):
        box = draw.textbbox((0, 0), text, font=LABEL_FONT)
        pad_x, pad_y = 13, 7
        x, y = position
        draw.rounded_rectangle(
            (x - pad_x, y - pad_y, x + (box[2] - box[0]) + pad_x, y + (box[3] - box[1]) + pad_y),
            radius=12,
            fill=COLORS["surface"],
            outline=COLORS["border"],
            width=2,
        )
        draw.text((x, y), text, font=LABEL_FONT, fill=COLORS["relation"])


def draw_table(x: int, y: int, width: int, title: str, rows):
    header_height = 116
    row_height = 84
    height = header_height + row_height * len(rows)

    draw.rounded_rectangle(
        (x + 10, y + 12, x + width + 10, y + height + 12),
        radius=25,
        fill="#DCE8F1",
    )
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=25,
        fill=COLORS["surface"],
        outline=COLORS["border"],
        width=4,
    )
    draw.rounded_rectangle(
        (x, y, x + width, y + header_height),
        radius=25,
        fill=COLORS["header"],
    )
    draw.rectangle(
        (x, y + header_height - 25, x + width, y + header_height),
        fill=COLORS["header"],
    )

    draw.text((x + 34, y + 26), title, font=TABLE_FONT, fill="#FFFFFF")
    badge_text = "RLS"
    badge_box = draw.textbbox((0, 0), badge_text, font=LEGEND_FONT)
    badge_width = badge_box[2] - badge_box[0] + 34
    draw.rounded_rectangle(
        (x + width - badge_width - 25, y + 30, x + width - 25, y + 84),
        radius=20,
        fill=COLORS["header_alt"],
        outline="#74B7DB",
        width=2,
    )
    draw.text(
        (x + width - badge_width - 8, y + 41),
        badge_text,
        font=LEGEND_FONT,
        fill="#FFFFFF",
    )

    for index, (key_type, name, data_type, constraints) in enumerate(rows):
        row_y = y + header_height + index * row_height
        if index % 2:
            draw.rectangle((x + 2, row_y, x + width - 2, row_y + row_height), fill=COLORS["row_alt"])
        if index:
            draw.line((x + 25, row_y, x + width - 25, row_y), fill="#D5E2EC", width=2)

        marker_x = x + 30
        if key_type:
            marker_color = COLORS[key_type.lower()]
            draw.rounded_rectangle(
                (marker_x, row_y + 22, marker_x + 68, row_y + 62),
                radius=9,
                fill=marker_color,
            )
            marker_box = draw.textbbox((0, 0), key_type, font=LEGEND_FONT)
            marker_text_x = marker_x + (68 - (marker_box[2] - marker_box[0])) / 2
            draw.text((marker_text_x, row_y + 27), key_type, font=LEGEND_FONT, fill="#FFFFFF")
            name_x = x + 118
        else:
            name_x = x + 32

        draw.text((name_x, row_y + 24), name, font=ROW_SEMIBOLD_FONT, fill=COLORS["text"])

        type_box = draw.textbbox((0, 0), data_type, font=ROW_FONT)
        type_x = x + width - 32 - (type_box[2] - type_box[0])
        draw.text((type_x, row_y + 24), data_type, font=ROW_FONT, fill=COLORS["muted"])

        if constraints:
            constraint_box = draw.textbbox((0, 0), constraints, font=LEGEND_FONT)
            constraint_x = type_x - 22 - (constraint_box[2] - constraint_box[0])
            if constraint_x > name_x + 220:
                draw.text((constraint_x, row_y + 28), constraints, font=LEGEND_FONT, fill=COLORS["unique"])

    return (x, y, x + width, y + height)


# Relacionamentos são desenhados antes das tabelas para permanecerem ao fundo.
relationship(
    [(1080, 280), (1400, 280)],
    "1",
    "0..N",
    [(1115, 210), (1280, 210)],
)
relationship(
    [(1900, 532), (1900, 1800)],
    "1",
    "0..N",
    [(1930, 690), (1930, 1680)],
)
relationship(
    [(1280, 2200), (1400, 2200)],
    "1",
    "0..1",
    [(1268, 2125), (1320, 2125)],
)

# Associação existente na aplicação, mas não protegida por chave estrangeira.
dashed_line([(1500, 532), (1240, 650), (1240, 1800)], COLORS["logical"], width=6, dash=24, gap=16)
logical_label = "id_veiculo — associação lógica, sem FK"
logical_box = draw.textbbox((0, 0), logical_label, font=LEGEND_FONT)
draw.rounded_rectangle(
    (1110, 1120, 1110 + (logical_box[2] - logical_box[0]) + 30, 1180),
    radius=12,
    fill=COLORS["surface"],
    outline=COLORS["border"],
    width=2,
)
draw.text((1125, 1133), logical_label, font=LEGEND_FONT, fill=COLORS["logical"])

draw_table(
    80,
    80,
    1000,
    "proprietarios",
    [
        ("PK", "id", "bigint", "identity"),
        ("", "nome", "text", "NOT NULL"),
        ("", "cpf", "text", "UNIQUE"),
    ],
)

draw_table(
    1400,
    80,
    1000,
    "veiculos",
    [
        ("PK", "id", "bigint", "identity"),
        ("", "placa", "text", "UNIQUE"),
        ("", "uid_rfid", "text", "UNIQUE / NULL"),
        ("FK", "proprietario_id", "bigint", "NOT NULL"),
    ],
)

draw_table(
    80,
    750,
    1000,
    "usuarios_concessionarias",
    [
        ("PK", "id", "bigint", "identity"),
        ("", "usuario", "text", "UNIQUE"),
        ("", "senha_hash", "text", "NOT NULL"),
        ("", "concessionaria_id", "text", "NOT NULL"),
        ("", "concessionaria_nome", "text", "NOT NULL"),
        ("", "faixas_permitidas", "text", "NOT NULL"),
        ("", "ativo", "smallint", "DEFAULT 1"),
        ("", "criado_em", "text", "NOT NULL"),
    ],
)

draw_table(
    80,
    1800,
    1200,
    "eventos_passagem",
    [
        ("PK", "id", "bigint", "identity"),
        ("", "id_veiculo", "text", "NOT NULL"),
        ("", "faixa", "integer", "> 0"),
        ("", "timestamp_evento", "text", "NOT NULL"),
        ("", "sensor_id", "text", "NULL"),
        ("", "origem", "text", "NULL"),
        ("", "valor", "double precision", "DEFAULT 5.0"),
        ("", "processado", "smallint", "DEFAULT 0"),
        ("", "anomalia", "text", "NULL"),
    ],
)

draw_table(
    1400,
    1800,
    1000,
    "cobrancas",
    [
        ("PK", "id", "bigint", "identity"),
        ("FK", "evento_id", "bigint", "UNIQUE"),
        ("FK", "veiculo_id", "bigint", "NOT NULL"),
        ("", "valor", "double precision", "DEFAULT 5.0"),
        ("", "status", "text", "pendente / pago"),
        ("", "timestamp_criacao", "text", "NOT NULL"),
    ],
)

# Legenda e observações sobre ligações que existem apenas na camada da aplicação.
legend_y = 3040
draw.rounded_rectangle(
    (80, legend_y, 2400, 3320),
    radius=24,
    fill=COLORS["note"],
    outline=COLORS["border"],
    width=3,
)
draw.line((130, legend_y + 55, 280, legend_y + 55), fill=COLORS["relation"], width=8)
draw.text((315, legend_y + 34), "Relacionamento por chave estrangeira", font=NOTE_FONT, fill=COLORS["text"])
dashed_line([(1250, legend_y + 55), (1400, legend_y + 55)], COLORS["logical"], width=6, dash=20, gap=12)
draw.text((1435, legend_y + 34), "Associação lógica da aplicação", font=NOTE_FONT, fill=COLORS["text"])
draw.text(
    (130, legend_y + 125),
    "Concessionária ↔ passagem: faixas_permitidas é comparada com faixa no backend;",
    font=NOTE_FONT,
    fill=COLORS["muted"],
)
draw.text(
    (130, legend_y + 180),
    "não há chave estrangeira nem tabela concessionarias no modelo atual.",
    font=NOTE_FONT,
    fill=COLORS["muted"],
)

image.save(OUTPUT, format="PNG", dpi=(300, 300), optimize=True)
print(OUTPUT)

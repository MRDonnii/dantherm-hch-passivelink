"""Render a synthetic feature tour for the released Home Assistant integration.

Requires Pillow. The values are examples; the frames are an illustration, not
screenshots of a Home Assistant installation.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "images" / "0.8.1-beta.8" / "ha-integration-tour.gif"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1200, 660
BG, CARD, WHITE, MUTED, CYAN, GREEN = "#07151f", "#102633", "#eff8fb", "#a8bec8", "#50c9e8", "#67d5ac"


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def box(draw, xy, fill=CARD, outline="#31515e", radius=20):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2)


def label(draw, xy, value, size=24, color=WHITE, bold=False):
    draw.text(xy, value, font=font(size, bold), fill=color)


def card(draw, xy, title, value, note, accent=CYAN):
    x0, y0, x1, y1 = xy
    box(draw, xy)
    draw.rounded_rectangle((x0 + 18, y0 + 20, x0 + 24, y1 - 20), radius=3, fill=accent)
    label(draw, (x0 + 43, y0 + 24), title, 21, MUTED)
    label(draw, (x0 + 43, y0 + 65), value, 34, WHITE, True)
    label(draw, (x0 + 43, y0 + 115), note, 18, MUTED)


def frame(index):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((43, 31, 1157, 116), radius=20, fill="#0d303e")
    label(d, (67, 52), "DANTHERM HCH5 CONTROL", 28, WHITE, True)
    label(d, (824, 59), "HOME ASSISTANT  ·  0.8.1-beta.8", 17, CYAN)

    titles = ["Data og styring samlet i HA", "Se anlægget i Home Assistant", "Styring med Pi som sikker master", "Rumdata, energi og diagnose"]
    label(d, (52, 144), titles[index], 34, WHITE, True)
    label(d, (52, 197), "Illustration med eksempelværdier · ingen live data", 18, MUTED)

    if index == 0:
        box(d, (55, 262, 350, 445)); box(d, (453, 262, 748, 445)); box(d, (851, 262, 1146, 445))
        label(d, (89, 289), "HCH5 / HAC1", 29, WHITE, True)
        label(d, (89, 344), "RS485-telemetri", 21, MUTED)
        label(d, (487, 289), "Raspberry Pi", 29, WHITE, True)
        label(d, (487, 344), "Controller + API", 21, MUTED)
        label(d, (885, 289), "Home Assistant", 27, WHITE, True)
        label(d, (885, 344), "Entiteter + sensorer", 20, MUTED)
        d.line((353, 353, 448, 353), fill=CYAN, width=7); d.polygon([(449, 353), (430, 343), (430, 363)], fill=CYAN)
        d.line((751, 353, 846, 353), fill=GREEN, width=7); d.polygon([(847, 353), (828, 343), (828, 363)], fill=GREEN)
        label(d, (95, 493), "HA sender hensigt og rumdata til Pi; Pi afgør sikre RS485-skriverier.", 21, MUTED)
    elif index == 1:
        card(d, (55, 262, 585, 420), "CO₂ i anlægget", "620 ppm", "Målt af HCH5 / HAC1")
        card(d, (615, 262, 1145, 420), "Tilluft", "20,9 °C", "Sensorværdi i HA", GREEN)
        card(d, (55, 438, 585, 596), "Ventilator", "1.740 rpm", "Faktisk omdrejningstal", GREEN)
        card(d, (615, 438, 1145, 596), "Varmegenvinding", "76 %", "Beregnet af temperaturer")
    elif index == 2:
        card(d, (55, 262, 585, 420), "Drift", "Smart Auto", "Local Auto · Smart Auto · Manuel")
        card(d, (615, 262, 1145, 420), "Ventilationsniveau", "OFF – 6", "Tidsstyret OFF og manuelle trin", GREEN)
        card(d, (55, 438, 585, 596), "Hurtig boost", "15 / 30 / 60 min", "Knapper i HA", GREEN)
        card(d, (615, 438, 1145, 596), "Eftervarme", "21 °C", "Setpunkt via controller-API")
    else:
        card(d, (55, 262, 585, 420), "Smart Auto-rum", "CO₂ · RH · PM2.5", "Vælg kun gyldige HA-sensorer")
        card(d, (615, 262, 1145, 420), "Luftbalance", "Auto / fast", "Kanalforhold og driftsstatus", GREEN)
        card(d, (55, 438, 585, 596), "Energi", "kWh · kr", "Målt strøm eller Pi-estimat", GREEN)
        card(d, (615, 438, 1145, 596), "Diagnose", "Filter · bus · Pi", "Tilstand og advarsler")

    for dot in range(4):
        d.ellipse((1056 + dot * 26, 625, 1066 + dot * 26, 635), fill=CYAN if dot == index else "#45606a")
    return img


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [frame(i) for i in range(4)]
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=[2000] * 4, loop=0, optimize=False, disposal=2)
    print(OUTPUT)

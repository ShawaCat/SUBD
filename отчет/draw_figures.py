"""Генерация рисунков 1 и 2 для отчёта по структуре программы.

Рисунок 1 — функции программного обеспечения (Общее.png).
Рисунок 2 — блоки информационной системы (Модули.png).

Кроме PNG сохраняются файлы Блоксхема.json и Залуав.json в формате
редактора блок-схем, которым пользовались авторы отчёта
(блоки с координатами центра и стрелки с узлами ломаной;
индексы коннекторов: 0 — верх, 1 — право, 2 — низ, 3 — лево).

Запуск:  python3 отчет/draw_figures.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SCALE = 2                       # масштаб растеризации (для чёткости)
FONT_SIZE = 14
LINE_W = 2
ARROW = 8
PAD_X, PAD_Y = 10, 7
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE * SCALE)
LINE_H = FONT_SIZE * 1.2


def text_size(text):
    lines = text.split("\n")
    width = max(FONT.getlength(line) for line in lines) / SCALE
    return width, len(lines) * LINE_H


class Diagram:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.blocks = []            # dict(x, y, w, h, text) — x, y центр
        self.arrows = []            # dict(start, end, sc, ec, nodes)
        self.lines = []             # ломаные без стрелок (служебные)
        self.notes = []             # подписи без рамки: (x, y, text)

    # ---- блоки -------------------------------------------------------
    def block(self, x, y, text, min_w=100, w=None, h=None):
        tw, th = text_size(text)
        width = w or max(min_w, round(tw + 2 * PAD_X))
        height = h or round(th + 2 * PAD_Y)
        self.blocks.append(dict(x=x, y=y, w=width, h=height, text=text))
        return len(self.blocks) - 1

    def top(self, i):
        b = self.blocks[i]
        return b["x"], b["y"] - b["h"] / 2

    def bottom(self, i):
        b = self.blocks[i]
        return b["x"], b["y"] + b["h"] / 2

    def left(self, i):
        b = self.blocks[i]
        return b["x"] - b["w"] / 2, b["y"]

    def right(self, i):
        b = self.blocks[i]
        return b["x"] + b["w"] / 2, b["y"]

    # ---- стрелки -----------------------------------------------------
    def arrow(self, start, end, sc, ec, nodes):
        """Стрелка от блока start к блоку end по узлам nodes."""
        self.arrows.append(dict(start=start, end=end, sc=sc, ec=ec,
                                nodes=[(float(x), float(y)) for x, y in nodes]))

    def tree_down(self, parent, children, bus_y, head=True):
        """Родитель сверху, потомки снизу: шина на высоте bus_y."""
        px, py = self.bottom(parent)
        for child in children:
            cx, cy = self.top(child)
            self.arrow(parent, child, 2, 0, [(px, py), (px, bus_y), (cx, bus_y), (cx, cy)])

    def side_bus(self, parent, children, side="left", offset=14):
        """Потомки столбиком под родителем, шина сбоку (как у авторов)."""
        if side == "left":
            px, py = self.left(parent)
            bx = px - offset
            for child in children:
                cx, cy = self.left(child)
                self.arrow(parent, child, 3, 3, [(px, py), (bx, py), (bx, cy), (cx, cy)])
        else:
            px, py = self.right(parent)
            bx = px + offset
            for child in children:
                cx, cy = self.right(child)
                self.arrow(parent, child, 1, 1, [(px, py), (bx, py), (bx, cy), (cx, cy)])
        return bx

    # ---- отрисовка ---------------------------------------------------
    def _poly(self, draw, pts, head_end=True, head_start=False):
        s = SCALE
        pts_s = [(x * s, y * s) for x, y in pts]
        draw.line(pts_s, fill="black", width=LINE_W * s, joint="curve")
        if head_end:
            self._head(draw, pts_s[-2], pts_s[-1])
        if head_start:
            self._head(draw, pts_s[1], pts_s[0])

    def _head(self, draw, p_from, p_to):
        s = SCALE
        (x1, y1), (x2, y2) = p_from, p_to
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5 or 1
        ux, uy = dx / length, dy / length
        a = ARROW * s
        base = (x2 - ux * a, y2 - uy * a)
        p1 = (base[0] - uy * a * 0.5, base[1] + ux * a * 0.5)
        p2 = (base[0] + uy * a * 0.5, base[1] - ux * a * 0.5)
        draw.polygon([(x2, y2), p1, p2], fill="black")

    def render(self, path):
        s = SCALE
        img = Image.new("RGB", (self.width * s, self.height * s), "white")
        draw = ImageDraw.Draw(img)
        for a in self.arrows:
            self._poly(draw, a["nodes"], head_end=True, head_start=a.get("both", False))
        for ln in self.lines:
            self._poly(draw, ln, head_end=False)
        for b in self.blocks:
            x0 = (b["x"] - b["w"] / 2) * s
            y0 = (b["y"] - b["h"] / 2) * s
            x1 = (b["x"] + b["w"] / 2) * s
            y1 = (b["y"] + b["h"] / 2) * s
            draw.rectangle([x0, y0, x1, y1], fill="white", outline="black", width=LINE_W * s)
            lines = b["text"].split("\n")
            total_h = len(lines) * LINE_H * s
            ty = (b["y"] + b.get("text_dy", 0)) * s - total_h / 2
            for line in lines:
                lw = FONT.getlength(line)
                draw.text((b["x"] * s - lw / 2, ty), line, font=FONT, fill="black")
                ty += LINE_H * s
        for x, y, text in self.notes:
            draw.text((x * s, y * s), text, font=FONT, fill="black")
        img.save(path, optimize=True)
        return img

    def save_json(self, path):
        """Файл для редактора блок-схем авторов отчёта (координаты центра)."""
        ox, oy = self.width / 2, self.height / 2
        blocks = [dict(x=b["x"] - ox, y=b["y"] - oy, text=b["text"],
                       width=b["w"], height=b["h"], type="Блок", isMenuBlock=False,
                       fontSize=FONT_SIZE, textHeight=FONT_SIZE, isBold=False,
                       isItalic=False, textAlign="center", labelsPosition=1)
                  for b in self.blocks]
        arrows = [dict(startIndex=a["start"], endIndex=a["end"],
                       startConnectorIndex=a["sc"], endConnectorIndex=a["ec"],
                       nodes=[dict(x=x - ox, y=y - oy) for x, y in a["nodes"]],
                       counts=[1] * len(a["nodes"]))
                  for a in self.arrows]
        data = dict(blocks=blocks, arrows=arrows, x0=ox, y0=oy)
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def check_overlaps(self):
        for i, a in enumerate(self.blocks):
            for j, b in enumerate(self.blocks):
                if j <= i:
                    continue
                if (abs(a["x"] - b["x"]) < (a["w"] + b["w"]) / 2 + 6
                        and abs(a["y"] - b["y"]) < (a["h"] + b["h"]) / 2 + 6):
                    print(f"ПЕРЕСЕЧЕНИЕ: {a['text']!r} и {b['text']!r}")
            if a["x"] - a["w"] / 2 < 4 or a["x"] + a["w"] / 2 > self.width - 4:
                print(f"ВЫХОД ЗА ГРАНИЦУ: {a['text']!r}")


# =====================================================================
# Рисунок 1 — Функции программного обеспечения
# =====================================================================
def figure_1():
    d = Diagram(1180, 1420)
    TRUNK = 105
    GAP = 14

    def row_blocks(y, texts, left=None, right=None, center=None, gap=GAP, min_w=100):
        """Разместить блоки в ряд; привязка к левому/правому краю или центру."""
        widths = [max(min_w, round(text_size(t)[0] + 2 * PAD_X)) for t in texts]
        total = sum(widths) + gap * (len(texts) - 1)
        if left is not None:
            x = left
        elif right is not None:
            x = right - total
        else:
            x = center - total / 2
        ids = []
        for t, w in zip(texts, widths):
            ids.append(d.block(x + w / 2, y, t, w=w))
            x += w + gap
        return ids

    def center_of(ids):
        return (d.left(ids[0])[0] + d.right(ids[-1])[0]) / 2

    root = d.block(TRUNK, 40, "Функции ПО", min_w=130)

    def row(bus_y, parents):
        """Ветка от ствола к родителям ряда (горизонтальная шина)."""
        rx, ry = d.bottom(root)
        for p in parents:
            px, py = d.top(p)
            d.arrow(root, p, 2, 0, [(rx, ry), (TRUNK, bus_y), (px, bus_y), (px, py)])

    L = 135                      # левая граница блоков (правее ствола)
    R = d.width - 15             # правая граница блоков

    # --- ряд 1: отображение и представление данных ---------------------
    tabs = row_blocks(270, ["Таблица\nпроектов/НИР", "Таблица НТП", "Таблица ВУЗ"], left=L)
    show = d.block(center_of(tabs), 170, "Отображение данных\n(меню «База данных»)")
    d.tree_down(show, tabs, 230)

    geo = row_blocks(360, ["По НТП", "По географии (округ,\nрегион, город, ВУЗ)"], right=R)
    filt = d.block(center_of(geo), 270, "Фильтрация", min_w=120)
    d.tree_down(filt, geo, 325)
    sort = d.block(d.left(filt)[0] - GAP - 85, 270, "Сортировка по ключу\n(НТП, НИР)")
    pres = d.block(center_of([sort, filt]), 170, "Представление данных\n(таблица проектов/НИР)")
    d.tree_down(pres, [sort, filt], 230)
    row(118, [show, pres])

    # --- ряд 2: редактирование -----------------------------------------
    ops = row_blocks(555, ["Добавление\nзаписи", "Изменение\nзаписи", "Удаление\nзаписи"], left=L)
    add, chg, dele = ops
    edit = d.block(center_of(ops), 460, "Редактирование данных\n(таблица проектов/НИР)")
    row(415, [edit])
    d.tree_down(edit, ops, 515)

    ctrl = d.block(center_of([add, chg]), 650, "Контроль корректности\nвводимых данных")
    conf = d.block(d.blocks[dele]["x"], 650, "Подтверждение\nудаления")
    ax, ay = d.bottom(add)
    cx_, cy_ = d.bottom(chg)
    tx, ty = d.top(ctrl)
    d.arrow(add, ctrl, 2, 0, [(ax, ay), (ax, 605), (tx, 605), (tx, ty)])
    d.arrow(chg, ctrl, 2, 0, [(cx_, cy_), (cx_, 605), (tx, 605), (tx, ty)])
    d.arrow(dele, conf, 2, 0, [d.bottom(dele), d.top(conf)])

    # --- ряд 3: поддержание целостности --------------------------------
    recalc = row_blocks(860, ["Пересчёт таблицы НИР:\nИсп_орг по коду ВУЗ,\nплан по кварталам",
                              "Пересчёт таблицы НТП:\nКол_п, План_фин,\nплан по кварталам",
                              "Пересчёт фактического\nфинансирования НТП\n(Факт_фин, Ф_фин_1–4)"],
                       left=L)
    integ = d.block(center_of(recalc), 755,
                    "Поддержание целостности («Пересчёт БД»:\n"
                    "по команде меню и автоматически после\n"
                    "редактирования и распределения финансирования)")
    row(705, [integ])
    d.tree_down(integ, recalc, 820)

    # --- ряд 4: анализ и финансирование --------------------------------
    an = row_blocks(1070, ["Распределение\nНИР по ВУЗ", "Распределение\nНИР по НТП",
                           "Распределение\nНИР по характеру"], left=L)
    anal = d.block(center_of(an), 965, "Анализ\n(с учётом фильтра)")
    d.tree_down(anal, an, 1025)
    fn = row_blocks(1070, ["Расчёт текущего\nфактического\nфинансирования",
                           "Распределение суммы\n(процента) на квартал\nпропорц. План_фин НИР",
                           "Запись\nраспределения\nв базу данных"], right=R)
    fin = d.block(center_of(fn), 965, "Финансирование")
    d.tree_down(fin, fn, 1025)
    row(920, [anal, fin])

    # --- ряд 5: документы и служебные функции --------------------------
    dc = row_blocks(1290, ["Распоряжение на\nфинансирование\n(ведомость по ВУЗ)",
                           "Результаты анализа\n(с условиями\nфильтрации)"], left=L)
    docs = d.block(center_of(dc), 1185, "Выпуск отчётных\nи распорядительных\nдокументов (PDF)")
    d.tree_down(docs, dc, 1245)
    sv = row_blocks(1290, ["Справка\n(help.txt)", "Выход"], center=d.blocks[fin]["x"])
    serv = d.block(center_of(sv), 1185, "Служебные функции")
    d.tree_down(serv, sv, 1245)
    row(1130, [docs, serv])

    d.check_overlaps()
    return d


# =====================================================================
# Рисунок 2 — Блоки информационной системы
# =====================================================================
def figure_2():
    d = Diagram(1400, 690)
    PITCH = 228
    X0 = 125
    KID_W = 170
    xs = [X0 + i * PITCH for i in range(6)]
    PY = 180                       # родители
    CY = [270, 340, 410]           # потомки
    DOC_Y = 500
    DB_Y = 615

    root = d.block((xs[2] + xs[3]) / 2, 40, "Информационная система\n(main.py)")

    names = [
        "Редактирование\nданных",
        "Упорядочивание\nданных",
        "Вывод\nданных",
        "Пересчёт БД\n(поддержание\nцелостности)",
        "Анализ\n(с учётом фильтра)",
        "Финансирование\n(finans.py)",
    ]
    parents = [d.block(x, PY, n, min_w=KID_W) for x, n in zip(xs, names)]
    d.tree_down(root, parents, 110)

    def column(ix, texts):
        return [d.block(xs[ix], CY[i], t, w=KID_W) for i, t in enumerate(texts)]

    edit_kids = column(0, ["Добавление\nзаписи", "Изменение\nзаписи", "Удаление\nзаписи"])
    order_kids = column(1, ["Сортировка по ключу\n(НТП, НИР)",
                            "Фильтрация (НТП,\nокруг, регион,\nгород, ВУЗ)"])
    out_kids = column(2, ["Таблица\nпроектов/НИР", "Таблица\nНТП", "Таблица\nВУЗ"])
    rec_kids = column(3, ["Пересчёт\nтаблицы НИР", "Пересчёт\nтаблицы НТП"])
    an_kids = column(4, ["Распределение\nНИР по ВУЗ", "Распределение\nНИР по НТП",
                         "Распределение\nНИР по характеру"])
    fin_kids = column(5, ["Расчёт текущего\nфинансирования",
                          "Распределение\nсредств по ВУЗ",
                          "Запись в базу\nданных"])

    bus_edit = d.side_bus(parents[0], edit_kids, "left")
    bus_order = d.side_bus(parents[1], order_kids, "left")
    bus_out = d.side_bus(parents[2], out_kids, "right")
    bus_rec = d.side_bus(parents[3], rec_kids, "left")
    bus_an = d.side_bus(parents[4], an_kids, "left")
    bus_fin = d.side_bus(parents[5], fin_kids, "left")

    # --- документы -----------------------------------------------------
    doc_an = d.block(xs[4], DOC_Y, "Отчёт о результатах\nанализа (PDF,\npdf_export.py)", w=KID_W)
    doc_fin = d.block(xs[5], DOC_Y, "Распоряжение о\nфинансировании ВУЗ\n(PDF, finans_pdf.py)", w=KID_W)

    def collect_right(sources, target):
        tx, ty = d.right(target)
        bx = max(d.right(s)[0] for s in sources) + 14
        for s in sources:
            sx, sy = d.right(s)
            d.arrow(s, target, 1, 1, [(sx, sy), (bx, sy), (bx, ty), (tx, ty)])

    collect_right(an_kids, doc_an)
    collect_right(fin_kids[1:], doc_fin)

    # --- упорядочивание действует на таблицу проектов/НИР --------------
    sx, sy = d.right(order_kids[0])
    tx, ty = d.left(out_kids[0])
    d.arrow(order_kids[0], out_kids[0], 1, 3, [(sx, sy), (tx, ty)])
    fx, fy = d.right(order_kids[1])
    mx = (fx + tx) / 2
    d.arrow(order_kids[1], out_kids[0], 1, 3, [(fx, fy), (mx, fy), (mx, ty), (tx, ty)])

    # --- база данных ---------------------------------------------------
    db = d.block(d.width / 2, DB_Y, "База данных res/data.db (SQLite)", w=1380, h=74)
    d.blocks[db]["text_dy"] = -22      # заголовок над вложенными таблицами
    tw = 300
    for i, t in enumerate(["ntp_proj — проекты/НИР", "ntp_prog — НТП", "VUZ — вузы"]):
        d.block(d.width / 2 + (i - 1) * (tw + 30), DB_Y + 12, t, w=tw, h=30)

    # связи столбцов с базой данных (стрелка к БД — запись, к блоку — чтение)
    def db_link(parent, bus_x, side, read=True, write=False):
        px, py = (d.left(parent) if side == "left" else d.right(parent))
        top_y = DB_Y - 37
        nodes = [(px, py), (bus_x, py), (bus_x, top_y)]
        sc = 3 if side == "left" else 1
        if write and read:
            d.arrows.append(dict(start=parent, end=db, sc=sc, ec=0, nodes=nodes, both=True))
        elif write:
            d.arrow(parent, db, sc, 0, nodes)
        else:
            d.arrow(db, parent, 0, sc, list(reversed(nodes)))

    d.notes.append((14, 14, "Стрелка к блоку БД — запись данных,\nот блока БД — чтение данных"))

    db_link(parents[0], bus_edit, "left", read=True, write=True)
    db_link(parents[1], bus_order, "left", read=True)
    db_link(parents[2], bus_out, "right", read=True)
    db_link(parents[3], bus_rec, "left", read=True, write=True)
    db_link(parents[4], bus_an, "left", read=True)
    db_link(parents[5], bus_fin, "left", read=True, write=True)

    d.check_overlaps()
    return d


if __name__ == "__main__":
    f1 = figure_1()
    f1.render(HERE / "Общее.png")
    f1.save_json(HERE / "Блоксхема.json")

    f2 = figure_2()
    f2.render(HERE / "Модули.png")
    f2.save_json(HERE / "Залуав.json")
    print("Готово")

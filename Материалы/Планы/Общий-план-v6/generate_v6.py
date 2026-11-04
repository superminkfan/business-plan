#!/usr/bin/env python3
"""Build the two v6 sheets from the saved project geometry. All coordinates in m."""
from pathlib import Path
import json
import hashlib
from html import escape

OUT = Path(__file__).resolve().parent
ASSETS = OUT.parent.parent
VIP = json.loads((OUT.parent / 'VIP-1-и-VIP-2/План-VIP-1-и-VIP-2-с-коридорами.context.json').read_text())
INK = '#26353b'
MUTED = '#5d6b72'
APPROX = '#426c89'
PAPER = '#ffffff'


class Sheet:
    def __init__(self, w, h, title, desc):
        self.w, self.h, self.items = w, h, []
        self.raw(f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>')
        self.raw('''<defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#36806a"/></marker>
        <pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="12" stroke="#b7564d" stroke-opacity=".12" stroke-width="3"/></pattern>
        </defs>''')
        self.raw(f'<rect width="{w}" height="{h}" fill="{PAPER}"/>')

    def raw(self, s):
        self.items.append(s)

    def text(self, x, y, value, size=26, fill=INK, anchor='start', weight=400, rotate=None):
        tr = '' if rotate is None else f' transform="rotate({rotate} {x} {y})"'
        self.raw(f'<text x="{x:.3f}" y="{y:.3f}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" dominant-baseline="middle"{tr}>{escape(str(value))}</text>')

    def line(self, x1, y1, x2, y2, color=INK, width=2, dash=None):
        d = '' if dash is None else f' stroke-dasharray="{dash}"'
        self.raw(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="{color}" stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill='none', stroke='none', sw=1, radius=0, attrs=''):
        self.raw(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{radius}" {attrs}/>')

    def save(self, name):
        content = f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" font-family="Arial, Helvetica, sans-serif">'+''.join(self.items)+'</svg>'
        (OUT / name).write_text(content)
        return content


DIMENSIONS = []


class Plan:
    def __init__(self, sheet, ox, oy, s, label_size=25):
        self.sh, self.ox, self.oy, self.s, self.fs = sheet, ox, oy, s, label_size

    def X(self, x): return self.ox + x*self.s
    def Y(self, y): return self.oy + y*self.s

    def rect(self, x, y, w, h, fill, stroke='none', sw=1.5, radius=0, attrs=''):
        self.sh.rect(self.X(x), self.Y(y), w*self.s, h*self.s, fill, stroke, sw, radius*self.s, attrs)

    def line(self, x1, y1, x2, y2, color=INK, width=3, dash=None):
        self.sh.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2), color, width, dash)

    def text(self, x, y, value, size=None, fill=INK, anchor='middle', rotate=None, weight=400):
        self.sh.text(self.X(x), self.Y(y), value, size or self.fs, fill, anchor, weight, rotate)

    def path(self, pts, fill='none', stroke=INK, sw=3, dash=None, arrow=False, attrs=''):
        d = ' '.join(('M' if i == 0 else 'L')+f'{self.X(x):.3f} {self.Y(y):.3f}' for i, (x,y) in enumerate(pts))
        self.sh.raw(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" '+(f'stroke-dasharray="{dash}" ' if dash else '')+('marker-end="url(#arrow)" ' if arrow else '')+attrs+'/>')

    def label(self, x, y, label, vertical=False, known=False, size=24):
        px, py = self.X(x), self.Y(y)
        width = max(26, len(label)*size*.54+14)
        if vertical:
            self.sh.raw(f'<g transform="rotate(-90 {px:.3f} {py:.3f})">')
        self.sh.rect(px-width/2, py-size*.64, width, size*1.28, PAPER, radius=2)
        self.sh.text(px, py+1, label, size, INK if known else APPROX, 'middle')
        if vertical:
            self.sh.raw('</g>')

    def dh(self, x1, x2, y, ref=None, label=None, known=False, size=24, label_x=None):
        color = INK if known else APPROX
        if ref is not None:
            self.line(x1, ref, x1, y+.06, '#b8c2c7', 1)
            self.line(x2, ref, x2, y+.06, '#b8c2c7', 1)
        self.line(x1, y, x2, y, color, 1.4)
        tick = 6/self.s
        for x in [x1, x2]: self.line(x-tick, y+tick, x+tick, y-tick, color, 1.6)
        value = label if label else ('' if known else '≈')+f'{x2-x1:.2f}'.replace('.', ',')
        self.label((x1+x2)/2 if label_x is None else label_x, y, value, known=known, size=size)
        DIMENSIONS.append(dict(axis='x', start=[x1, ref], end=[x2, ref], line=y, value=value, known=known))

    def dv(self, y1, y2, x, ref=None, label=None, known=False, size=24):
        color = INK if known else APPROX
        if ref is not None:
            self.line(ref, y1, x+.06, y1, '#b8c2c7', 1)
            self.line(ref, y2, x+.06, y2, '#b8c2c7', 1)
        self.line(x, y1, x, y2, color, 1.4)
        tick = 6/self.s
        for y in [y1, y2]: self.line(x-tick, y+tick, x+tick, y-tick, color, 1.6)
        value = label if label else ('' if known else '≈')+f'{y2-y1:.2f}'.replace('.', ',')
        self.label(x, (y1+y2)/2, value, vertical=True, known=known, size=size)
        DIMENSIONS.append(dict(axis='y', start=[ref, y1], end=[ref, y2], line=x, value=value, known=known))

    def column(self, x, y):
        self.rect(x,y,.41,.41,'#aab6b9',INK,2.1, attrs='data-column="true"')
        self.line(x,y,x+.41,y+.41,INK,1.4)
        self.line(x+.41,y,x,y+.41,INK,1.4)

    def person(self, x, y, rotation=0, name='Человек для масштаба'):
        # Top view, overall shoulder span exactly 0.50 m and depth 0.30 m.
        px, py, s = self.X(x), self.Y(y), self.s
        self.sh.raw(f'<g transform="translate({px:.3f} {py:.3f}) rotate({rotation})" data-person="true"><title>{escape(name)} · плечи 0,50 м, вид сверху</title>')
        self.sh.raw(f'<ellipse cx="0" cy="{.018*s}" rx="{.25*s}" ry="{.105*s}" fill="#58747d"/>')
        self.sh.raw(f'<ellipse cx="0" cy="{-.025*s}" rx="{.155*s}" ry="{.125*s}" fill="#58747d"/>')
        self.sh.raw(f'<circle cx="0" cy="{-.035*s}" r="{.082*s}" fill="#e5ecec" stroke="#3e5863" stroke-width="1.5"/>')
        self.sh.raw('</g>')

    def vip(self, detail=False, people=True):
        self.rect(0,0,3.20,3.93,'#f0f6f2', attrs='data-vip="1"')
        self.path([[5.70,0],[8.37,0],[8.37,5.18],[4.60,5.18],[4.60,1.30],[5.70,1.30],[5.70,0]], '#f0f6f2', 'none', 0, attrs='data-vip="2"')
        for b in [(3.30,0,1.20,3.93),(4.50,0,1.10,1.20),(0,3.93,4.50,1.25)]: self.rect(*b,'#f0f1ef')
        self.line(3.25,0,3.25,.45,width=5)
        self.line(3.25,1.35,3.25,3.93,width=5)
        self.line(0,3.93,3.25,3.93,width=5)
        self.line(3.25,.45,3.25,1.35,'#89979c',1.5,'5 5')
        self.line(5.65,0,5.65,.16,width=5)
        self.path(VIP['treatments']['storage']['partition'],sw=5)
        self.line(5.65,.16,6.55,.16,'#668074',2)
        self.sh.raw(f'<path d="M{self.X(5.65)} {self.Y(1.06)} A{.9*self.s} {.9*self.s} 0 0 0 {self.X(6.55)} {self.Y(.16)}" fill="none" stroke="#9aaba3" stroke-width="1.4" stroke-dasharray="5 5"/>')
        for b in VIP['vip1']['sofa']:
            self.rect(b['x'],b['y'],b['w'],b['h'],'#bad8c9','#719986',1.6,.05, 'data-vip1-sofa="true"')
        self.line(.37,1.42,.37,3.48,'#729c87',1)
        self.line(.37,3.48,2.17,3.48,'#729c87',1)
        for y in [2.1,2.8]: self.line(.38,y,1.03,y,'#729c87',1)
        self.line(1.62,2.83,1.62,3.46,'#729c87',1)
        self.rect(3.03,2.20,.17,1.30,INK,radius=.015,attrs='data-tv="vip1"')
        self.column(1.77,1.58)
        for key in ['sofa','return']:
            b = VIP[key]
            self.rect(b['x'],b['y'],b['w'],b['h'],'#bad8c9','#719986',1.6,.05, 'data-vip2-sofa="true"')
        self.line(8.19,2.38,8.19,5.02,'#729c87',1)
        for y in [3.23,4.16]: self.line(7.50,y,8.19,y,'#729c87',1)
        self.line(6.50,4.92,7.39,4.92,'#729c87',1)
        b=VIP['table'];self.rect(b['x'],b['y'],b['w'],b['h'],'#e7dfcd','#a49779',1.5,.04, 'data-table="vip2"')
        b=VIP['tv'];self.rect(b['x'],b['y'],b['w'],b['h'],INK, radius=.01,attrs='data-tv="vip2"')
        for b in VIP['poufs']:
            self.rect(b['x'],b['y'],b['w'],b['h'],'#c8dfd2','#719986',1.3,.06,'data-pouf="true"')
            self.text(b['x']+b['w']/2,b['y']+b['h']/2,'П',size=23)
        self.column(5.05,1.58)
        for b in VIP['treatments']['storage']['shelving']:
            self.rect(b['x'],b['y'],b['w'],b['h'],'#dcc694','#99814f',1.2,attrs='data-storage="board-games"')
            for f in [1/3,2/3]: self.line(b['x']+b['w']*f,b['y'],b['x']+b['w']*f,b['y']+b['h'],'#99814f',1)
        self.text(1.35,.35,'VIP №1',size=28,weight=500)
        self.text(1.35,.67,'≈12 м²',size=23,fill=MUTED)
        self.text(7.25,1.42,'VIP №2',size=28,weight=500)
        self.text(7.25,1.72,'≈17 м²',size=23,fill=MUTED)
        self.text(2.83,3.10,'ТВ / PS5',size=21,rotate=-90)
        self.text(4.92,3.66,'ТВ / PS5',size=21,rotate=-90)
        self.text(6.67,3.10,'Столик',size=21,rotate=-90)
        if not detail:
            self.text(5.21,2.61,'Настолки',size=21)
            self.text(1.65,4.19,'К №65',size=23)
        if people:
            self.person(2.59,2.40,90,'Посетитель VIP №1')
            self.person(5.92,3.58,90,'Посетитель VIP №2')

    def pc(self, x, y, vertical, index, reserve=False):
        w,h=(.75,1.2) if vertical else (1.2,.75)
        fill = '#ffffff' if reserve else '#c0daec'
        stroke = '#7299b4' if reserve else '#5c87a5'
        attrs = f'data-reserve="{index}" stroke-dasharray="7 6"' if reserve else f'data-pc="{index}"'
        self.rect(x,y,w,h,fill,stroke,1.5,.035,attrs)
        cx=(x+.8 if reserve or index==10 else x-.60) if vertical else x+.325
        cy=y+.29 if vertical else y-.60
        self.rect(cx,cy,.55,.55,'#ffffff' if reserve else '#e4e8e8',stroke if reserve else '#a3afb4',1.3,.08,'stroke-dasharray="7 6"' if reserve else '')
        # A narrow monitor mark makes the table direction legible.
        if not reserve:
            if vertical: self.line(x+(.61 if index!=10 else .13),y+.22,x+(.61 if index!=10 else .13),y+.98,'#52788f',2)
            else: self.line(x+.20,y+.62,x+1.0,y+.62,'#52788f',2)
        self.text(x+w/2,y+h/2,('+1' if reserve else str(index)),size=24,fill=APPROX if reserve else INK)

    def full(self, people=True, routes=True):
        for b in [(-1.49,-1.59,5.69,1.59),(4.20,-1.59,4.17,1.59),(-1.49,0,1.49,7.01)]: self.rect(*b,'#f0f1ef')
        self.path([[-1.49,7.01],[0,7.01],[0,5.18],[8.37,5.18],[8.37,13.77],[-1.49,13.77]],'#f1f6fa','none',0)
        self.rect(1.85,5.18,2.60,1.83,'#e9edef')
        self.vip(people=people)
        self.path([[-1.49,7.01],[-1.49,-1.59],[8.37,-1.59],[8.37,-1.18]],sw=6)
        self.line(8.37,-.18,8.37,8.45,width=6)
        self.line(4.20,-1.59,4.20,-1.10,width=4)
        self.line(4.20,-.20,4.20,0,width=4)
        self.line(0,0,4.60,0,width=6)
        self.line(5.50,0,8.37,0,width=6)
        self.line(0,0,0,5.78,width=6)
        self.line(0,6.68,0,7.01,width=6)
        self.line(0,5.18,.70,5.18,width=6)
        self.line(1.70,5.18,8.37,5.18,width=6)
        self.path([[8.37,9.55],[8.37,13.77],[-1.49,13.77],[-1.49,7.01],[.68,7.01]],sw=6)
        self.line(1.50,7.01,2.35,7.01,width=5)
        self.line(3.22,7.01,4.45,7.01,width=5)
        self.line(4.45,5.18,4.45,7.01,width=5)
        self.path([[1.85,7.01],[1.85,8.04],[4.45,8.04]],sw=5)
        self.rect(8.37,7.91,1.63,2.14,'#f0f1ef')
        self.rect(8.37,10.05,1.63,4.52,'#f0f1ef')
        self.path([[8.37,7.91],[10,7.91],[10,14.57],[8.37,14.57],[8.37,9.55]],sw=5)
        self.line(8.37,10.05,8.66,10.05,width=4)
        self.line(9.62,10.05,10,10.05,width=4)
        for i in range(7): self.line(8.53,11.45+i*.24,9.87,11.45+i*.24,'#b9c1c4',1.5)
        for i in range(5): self.line(5.60+i*.27,-1.50,5.60+i*.27,-.10,'#b9c1c4',1.5)
        for a,b in [(.35,1.50),(2.45,4.60),(10.10,13.35)]:
            self.line(8.42,a,8.42,b,'#849da9',2)
            self.line(8.50,a,8.50,b,'#849da9',2)
        for a,b in [(2.55,4.18),(6.06,7.64)]:
            self.line(a,13.82,b,13.82,'#849da9',2)
            self.line(a,13.90,b,13.90,'#849da9',2)
        self.text(1.42,-1.24,'№64 · общий коридор',size=24)
        self.text(7.3,-1.25,'№63 · 9,0 м²',size=24)
        self.text(-.77,2.25,'Общий коридор',size=23,rotate=-90)
        self.text(9.35,-1.08,'Улица',size=25)
        self.text(.84,5.60,'№65',size=25)
        self.text(.84,6.0,'2,3 м²',size=21,fill=MUTED)
        self.text(2.6,5.70,'№89',size=23)
        self.text(2.6,6.05,'2,0 м²',size=21,fill=MUTED)
        self.text(3.72,5.7,'WC · №90',size=22)
        self.text(3.72,6.05,'1,8 м²',size=21,fill=MUTED)
        self.text(3.15,7.48,'№92',size=23)
        self.text(9.18,8.34,'№99',size=24)
        self.text(9.18,8.69,'Вход',size=22)
        self.text(9.18,9.72,'2,2 м²',size=21,fill=MUTED)
        self.text(9.18,10.50,'Лестница',size=21)
        self.text(9.18,14.96,'Улица',size=25)
        # Open service line, no added walls.
        self.rect(4.55,5.30,.60,1.00,'#e5d9b9','#a99772',1.5,attrs='data-kitchen-table="true"')
        self.rect(4.55,6.30,.60,.60,'#e5e8e7','#8e9d9f',1.5,attrs='data-sink="true"')
        self.rect(4.67,6.40,.36,.34,'#f7fafb','#8e9d9f',1.2,.04)
        self.text(5.48,5.74,'Стол',size=22,anchor='start')
        self.text(5.48,6.58,'Мойка',size=22,anchor='start')
        self.rect(5.75,7.08,2.62,.73,'#d7e0e3','#859aa4',1.7,attrs='data-reception="true"')
        self.rect(7.00,6.35,.60,.60,'#e4e8e8','#a3afb4',1.3,.08)
        self.text(7.06,7.45,'Ресепшн',size=25)
        self.rect(-1.36,7.45,.60,.82,'#dce3e6','#a3afb4',1.3)
        self.text(-1.06,7.85,'Тех.',size=20)
        for i,y in enumerate([10.05,11.25,12.45]): self.pc(7.57,y,True,i+1)
        for i,x in enumerate([-1.34,-.14,1.06,2.26,3.46,4.66]): self.pc(x,13.02,False,i+4)
        self.pc(1.90,10.30,True,10)
        self.pc(3.65,10.30,True,11,True)
        self.pc(5.40,10.30,True,12,True)
        self.text(4.7,11.86,'Резерв +2 ПК',size=24,fill=APPROX)
        self.column(1.52,9.55)
        self.column(5.05,9.55)
        # Former display removed completely: no display rectangle or fixtures.
        self.rect(-1.49,9.55,1.70,1.90,'url(#hatch)','#b7564d',1.5,attrs='stroke-dasharray="6 6" data-fire-clear="true"')
        self.rect(-1.49,10.0,.14,.9,'#c97e72')
        for y,txt in [(10.10,'Пожарные'),(10.47,'щиты'),(10.86,'Доступ')]: self.text(-.60,y,txt,size=21,fill='#9b4d46')
        if routes:
            self.path([[.78,8.85],[6.50,8.85],[7.10,9.0],[9.18,9.0],[9.18,14.66]],stroke='#36806a',sw=3,arrow=True)
            self.path([[.78,8.85],[.78,6.26],[1.12,5.75],[1.12,4.60],[3.90,4.60],[3.90,.60],[5.05,.60],[5.05,-.62],[9.70,-.62]],stroke='#36806a',sw=3,dash='10 8',arrow=True)
            self.path([[.78,6.26],[-.72,6.26]],stroke='#8a969b',sw=2,dash='6 7')
        if people:
            for x,y,r,name in [(3.89,2.22,0,'Посетитель в коридоре'),(2.40,8.56,90,'Посетитель в зале'),(6.45,8.37,0,'Посетитель у ресепшна'),(2.95,12.01,180,'Посетитель у ПК'),(7.3,6.65,180,'Администратор')]:
                self.person(x,y,r,name)


def scale_bar(sh, x, y, s, label='Масштабная линейка · метры'):
    sh.text(x,y-30,label,23,MUTED)
    for i in range(5):
        sh.rect(x+i*s,y,s,13,INK if i%2==0 else PAPER,INK,1)
        sh.text(x+i*s,y+36,str(i),21,INK,'middle')
    sh.text(x+5*s,y+36,'5 м',21,INK,'middle')


def header(sh, number, title, sub):
    sh.text(100,85,'КОМПЬЮТЕРНЫЙ КЛУБ',25,MUTED,weight=500)
    sh.text(100,150,title,46,INK,weight=500)
    sh.text(100,207,sub,26,MUTED)
    sh.text(sh.w-100,90,'v6',52,INK,'end',500)
    sh.text(sh.w-100,145,f'Лист {number} / 2 · 17.10.2026',25,MUTED,'end')
    sh.line(100,250,sh.w-100,250,'#bbc7cc',1.5)


def detailed():
    sh=Sheet(4200,2970,'План клуба v6 — подробный план с размерами','Общий план, увеличенные VIP, размеры, привязки колонн, мебель и люди для масштаба. Все размеры в метрах. Знаком ≈ отмечены размеры эскиза до обмера.')
    header(sh,1,'План с размерами','10 ПК · 2 VIP с PS5 · резерв +2 ПК · витрина между колоннами убрана')
    p=Plan(sh,555,620,114)
    p.full()
    # Overall dimensions and source dimensions.
    p.dh(0,8.37,-2.28,ref=0,known=True,label='8,37 · №86',size=28)
    p.dh(-1.49,0,-2.82,ref=-1.59,size=24)
    p.dv(-1.59,0,-2.05,ref=-1.49,size=24)
    p.dv(0,5.18,9.28,ref=8.37,known=True,size=28)
    p.dv(5.18,13.77,11.65,ref=8.37,known=True,size=28)
    p.dv(7.01,13.77,-2.62,ref=-1.49,known=True,size=28)
    p.dv(-1.59,13.77,-3.62,ref=-1.49,label='≈15,36 · общий габарит эскиза',size=25)
    p.dh(-1.49,8.37,14.90,ref=13.77,known=True,size=28)
    p.dh(-1.34,5.86,14.25,ref=13.77,label='≈7,20 · 6 × 1,20',size=24)
    p.dv(10.05,13.65,10.70,ref=8.32,label='≈3,60 · 3 × 1,20',size=24)
    p.dh(5.86,7.57,12.12,ref=13.02,size=24)
    p.dv(11.50,12.42,6.55,ref=6.15,label='≈0,92',size=21)
    # Structural bindings in the lower hall, to left/top faces of columns.
    p.dh(-1.49,1.52,9.23,ref=9.55,size=23)
    p.dh(1.52,5.05,9.23,ref=9.55,size=23)
    p.dh(5.46,8.37,9.23,ref=9.55,size=23)
    p.dv(5.18,9.55,10.70,ref=8.37,label='≈4,37 · до грани колонн',size=24)
    p.dh(1.85,4.45,8.38,ref=8.04,size=24)
    p.dv(5.18,7.01,1.62,ref=1.85,size=22)
    p.dh(5.75,8.37,6.08,ref=7.08,size=24)
    p.dh(4.45,5.75,7.74,ref=7.08,size=22)
    p.dh(8.37,10,7.55,ref=7.91,size=23)
    p.dv(7.91,10.05,10.25,ref=10,size=22)
    p.dh(-1.49,.21,9.0,ref=9.55,size=22)
    p.dv(9.55,11.45,-1.98,ref=-1.49,size=22)
    p.dh(3.30,4.50,2.95,label='≈1,20',size=22)
    p.dv(3.93,5.18,2.87,label='≈1,25',size=22)
    p.dh(.70,1.70,5.38,label='≈1,00',size=21)
    p.dh(4.60,5.50,-.24,label='≈0,90',size=21)
    p.dv(8.45,9.55,8.03,label='≈1,10',size=21)
    p.text(5.05,-1.94,'Ориентир «5,64» на исходнике',size=22,fill=MUTED)
    p.text(9.5,-.28,'№63: вход / выход',size=21,fill='#36806a')
    p.text(3.47,10.08,'Свободная площадь',size=21,fill=MUTED)
    sh.text(100,2520,'01  ОБЩИЙ ПЛАН',29,INK,weight=500)
    scale_bar(sh,100,2600,114)
    sh.text(100,2700,'Размеры — м. Чёрные: подписи исходного плана.',25)
    sh.text(100,2742,'Синие с ≈: расчёт по геометрии сохранённого эскиза.',25,APPROX)
    sh.text(100,2784,'h = 4,37 м по исходнику · окна высоко · люди: плечи 0,50 м.',25,MUTED)
    sh.text(100,2826,'Площади VIP округлены; толщина стен показана условно.',24,MUTED)
    # Enlarged VIP panel; same geometry, more internal measurements.
    sh.text(2310,318,'02  VIP-КОМНАТЫ · УВЕЛИЧЕННЫЙ ФРАГМЕНТ',29,INK,weight=500)
    q=Plan(sh,2410,585,172,label_size=24)
    q.vip(detail=True,people=False)
    q.line(0,0,4.60,0,width=5)
    q.line(5.50,0,8.37,0,width=5)
    q.line(0,0,0,5.18,width=5)
    q.line(0,5.18,8.37,5.18,width=5)
    q.line(8.37,0,8.37,5.18,width=5)
    q.line(8.42,.35,8.42,1.50,'#849da9',2)
    q.line(8.50,.35,8.50,1.50,'#849da9',2)
    q.line(8.42,2.45,8.42,4.60,'#849da9',2)
    q.line(8.50,2.45,8.50,4.60,'#849da9',2)
    q.dh(0,8.37,-1.04,ref=0,label='8,37',known=True,size=26)
    q.dh(0,3.20,-.58,ref=0,size=25)
    q.dh(5.70,8.37,-.58,ref=0,size=25)
    q.dv(0,3.93,-.38,ref=0,size=25)
    q.dv(0,5.18,9.18,ref=8.37,size=25)
    q.dv(2.30,5.10,8.76,ref=8.37,size=24)
    q.dh(4.60,8.37,5.84,ref=5.18,size=25)
    q.dh(6.42,8.37,5.43,ref=5.10,size=24)
    q.dh(0,4.50,4.76,label='≈4,50',size=24,label_x=1.60)
    q.dv(3.93,5.18,3.0,label='≈1,25',size=23)
    q.dh(3.30,4.50,3.45,label='≈1,20',size=23)
    q.dv(.45,1.35,3.65,label='≈0,90',size=22)
    q.dv(.16,1.06,6.65,label='≈0,90',size=22)
    q.dh(0,1.77,1.10,ref=1.58,size=23)
    q.dh(1.77,2.18,1.10,ref=1.58,known=True,label='0,41',size=21)
    q.dh(2.18,3.20,1.10,ref=1.58,size=23)
    q.dv(0,1.58,2.48,ref=2.18,size=23)
    q.dh(1.05,1.77,2.30,label='≈0,72',size=21)
    q.dh(2.25,3.03,3.48,label='≈0,78',size=21)
    q.dh(.20,2.25,3.79,label='≈2,05',size=23)
    q.dh(4.60,5.05,1.43,ref=1.58,size=20)
    q.dh(5.05,5.46,1.43,ref=1.58,known=True,label='0,41',size=20)
    q.dh(5.46,5.76,1.43,ref=1.58,label='≈0,30',size=20)
    q.dh(6.27,7.07,2.15,ref=2.40,label='≈0,80',size=22)
    q.dv(2.40,3.80,6.05,ref=6.27,label='≈1,40',size=22)
    q.dh(7.07,7.47,3.98,label='≈0,40',size=20)
    q.dv(3.80,4.20,6.51,label='≈0,40',size=20)
    q.text(5.24,2.61,'Полки',size=21)
    q.text(7.28,2.01,'Диван у окна',size=21,fill=MUTED)
    q.text(1.0,4.26,'Связь с №65',size=22,fill=MUTED)
    # Compact dimensional register includes small furniture omitted from chains.
    sh.text(2310,1660,'03  МЕБЕЛЬ, ПРОЁМЫ И ПРИВЯЗКИ',29,INK,weight=500)
    sh.text(2310,1708,'Все значения ниже ≈, кроме сечения колонн 0,41 × 0,41 м.',23,APPROX)
    rows=[
      ('VIP №1 · диван','2,30 × 2,05','Глубина секций 0,85'),
      ('VIP №2 · диван','2,80 × 1,95','Глубина секций 0,90; у правой стены'),
      ('VIP №2 · столик','1,40 × 0,80','До обеих секций дивана по 0,40'),
      ('Пуфы VIP №2','0,65 × 0,65 / 0,60 × 0,60','Два отдельных места'),
      ('Полки у колонны','0,82 × 0,36 / 0,30 × 0,41','Доступ со стороны VIP №2'),
      ('ТВ / PS5 в обеих VIP','Экран по плану 1,30','VIP №2: до передней грани дивана 2,75'),
      ('Стол ПК / кресло','1,20 × 0,75 / 0,55 × 0,55','От стола до конца кресла: 1,35'),
      ('Ряды ПК','Нижний 7,20 / правый 3,60','Отступ слева 0,15; справа 0,05'),
      ('Стойка / кресло','2,62 × 0,73 / 0,60 × 0,60','От №92 до начала стойки 1,30'),
      ('Стол / мойка','1,00 × 0,60 / 0,60 × 0,60','Общая линия вдоль стены 1,60'),
      ('Технический шкаф','0,60 × 0,82','У левой стены зала'),
      ('Зона перед щитами','1,70 × 1,90','Условная свободная зона эскиза'),
      ('Проёмы VIP №1 / №2','0,90 / 0,90','№2: открывание внутрь'),
      ('Проёмы №86 / №99','0,90 / 1,10','Проём №65 → №86: 1,00'),
      ('Существующие колонны','0,41 × 0,41','Четыре колонны, без демонтажа'),
      ('Колонны VIP · X / Y','1,77 / 1,58 · 5,05 / 1,58','От верхнего левого угла №86'),
      ('Колонны зала · X / Y','1,52 / 9,55 · 5,05 / 9,55','Тот же ноль; привязка к левой/верхней грани'),
      ('Общие проходы','Левый 1,49 / верхний 1,59','Между VIP 1,20; нижняя связь 1,25'),
      ('Окна справа · длины','1,15 / 2,15 / 3,25','Сверху вниз; положение по эскизу'),
      ('Окна снизу · длины','1,63 / 1,58','Высота подоконников не измерена'),
    ]
    y=1768
    for i,(name,dims,note) in enumerate(rows):
        if i%2==0: sh.rect(2290,y-20,1800,42,'#f3f6f6')
        sh.text(2310,y,name,23)
        sh.text(2780,y,dims,23,APPROX)
        sh.text(3385,y,note,21,MUTED)
        y+=42
    sh.text(2310,2630,'Основа: v5 + общий план VIP от 16.10.2026.',24,MUTED)
    sh.text(2310,2672,'VIP №1: без оболочки колонны; новые три варианта ещё не выбраны.',23,MUTED)
    sh.text(2310,2714,'№88 — высокий щит автоматики; отдельной напольной зоны нет.',23,MUTED)
    sh.text(2310,2756,'Дверь №63 доступна для входа и выхода — подтверждено пользователем.',23,MUTED)
    sh.text(2310,2798,'Резерв +2 ПК показан условно: проходы с креслами ещё не подтверждены.',23,MUTED)
    sh.line(100,2880,4100,2880,'#bbc7cc',1.5)
    sh.text(100,2924,'Мебельный эскиз до обмера. Размеры проёмов, положения колонн и чистые проходы проверить на месте.',23,MUTED)
    sh.text(4100,2924,'v6 / 01',25,MUTED,'end')
    return sh.save('План-клуба-v6-с-размерами.svg')


def sketch():
    sh=Sheet(2100,2800,'План клуба v6 — простой эскиз','Обновлённые VIP, десять ПК, два условных места резерва, люди для масштаба. Витрина между нижними колоннами убрана.')
    header(sh,2,'Простой эскиз','10 ПК · 2 VIP с PS5 · 7 человек для масштаба')
    p=Plan(sh,500,505,127)
    p.full()
    p.dh(0,8.37,-1.86,ref=0,known=True,label='8,37 м',size=26)
    p.dv(0,5.18,9.3,ref=8.37,known=True,label='5,18 м',size=26)
    p.dv(7.01,13.77,-2.0,ref=-1.49,known=True,label='6,76 м',size=26)
    p.dv(5.18,13.77,11.0,ref=8.37,known=True,label='8,59 м',size=26)
    p.dh(-1.49,8.37,14.93,ref=13.77,known=True,label='9,86 м',size=26)
    p.text(3.50,9.90,'Свободно',size=23,fill=MUTED)
    p.text(9.32,-.30,'Вход / выход №63',size=21,fill='#36806a')
    p.text(4.05,3.1,'≈1,20 м',size=22,rotate=-90)
    sh.line(100,2460,2000,2460,'#bbc7cc',1.5)
    sh.rect(100,2500,24,24,'#c0daec','#5c87a5')
    sh.text(140,2512,'ПК',25)
    sh.rect(270,2500,24,24,'#bad8c9','#719986')
    sh.text(310,2512,'VIP / PS5',25)
    sh.line(560,2512,620,2512,'#36806a',3)
    sh.text(640,2512,'Маршруты к выходам',25)
    h=Plan(sh,1225,2512,127)
    h.person(0,0)
    sh.text(1275,2512,'Плечи 0,50 м',25)
    scale_bar(sh,100,2605,127)
    sh.text(880,2580,'Две VIP по последнему общему плану от 16.10.2026.',24,MUTED)
    sh.text(880,2622,'Пунктирные ПК — условный резерв. Размеры — до обмера.',24,MUTED)
    sh.text(880,2664,'Подробные размеры — на листе 1.',24,MUTED)
    sh.line(100,2715,2000,2715,'#bbc7cc',1.5)
    sh.text(100,2755,'Мебельный эскиз · 17.10.2026',24,MUTED)
    sh.text(2000,2755,'v6 / 02',25,MUTED,'end')
    return sh.save('План-клуба-v6-эскиз.svg')


if __name__ == '__main__':
    detailed_svg=detailed()
    detail_dimensions=DIMENSIONS.copy()
    sketch_svg=sketch()
    html='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>План клуба · v6</title><style>
    *{box-sizing:border-box}body{margin:0;background:#e9edef;color:#26353b;font-family:Arial,Helvetica,sans-serif}header{padding:20px 28px;display:flex;gap:24px;align-items:center;flex-wrap:wrap;background:#fff;border-bottom:1px solid #bdc8cd}h1{font-size:21px;margin:0}nav{display:flex;gap:10px;flex-wrap:wrap}button,a{font:inherit}button{padding:9px 15px;border:1px solid #879ba5;background:white;border-radius:4px;color:#26353b;cursor:pointer}button[aria-pressed=true]{background:#263f49;color:white}a{color:#426c89;margin-left:10px}.sheet{margin:20px auto;background:white;max-width:1700px}.sheet svg{display:block;width:100%;height:auto}[hidden]{display:none!important}.tools{display:flex;gap:8px;align-items:center}.note{margin:12px 28px;font-size:14px;color:#53656d}@media print{header,.note{display:none}.sheet{margin:0;max-width:none;width:408mm;height:284mm;break-after:page}.sheet svg{width:100%;height:100%}.sheet[hidden]{display:block!important}body{background:white}@page{size:A3 landscape;margin:6mm}}</style></head><body>
    <header><h1>План клуба · версия 6</h1><nav aria-label="Листы"><button type="button" data-sheet="detail" aria-pressed="true">1 · С размерами</button><button type="button" data-sheet="sketch" aria-pressed="false">2 · Простой эскиз</button></nav><div class="tools"><button type="button" id="print">Печать</button><a href="План-клуба-v6-с-размерами.png">PNG с размерами</a><a href="План-клуба-v6-эскиз.png">PNG эскиз</a></div></header>
    <p class="note">Размеры — метры. ≈ означает приблизительный размер по эскизу. Для увеличения без потери качества используйте SVG из этой папки.</p>
    <main><section id="detail" class="sheet" aria-label="Подробный план с размерами">'''+detailed_svg+'''</section><section id="sketch" class="sheet" hidden aria-label="Простой эскиз">'''+sketch_svg+'''</section></main>
    <script>document.querySelectorAll('[data-sheet]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.sheet').forEach(s=>s.hidden=s.id!==button.dataset.sheet);document.querySelectorAll('[data-sheet]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)))}));document.getElementById('print').addEventListener('click',()=>window.print());</script></body></html>'''
    (OUT/'План-клуба-v6.html').write_text(html)
    ctx={
      'version':6,'date':'2026-10-17','units':'m',
      'sourceFiles':['../../Архив/План-v5/План-клуба-v5.source.html','../../Оригиналы/Исходный-план-помещения.jpg','../VIP-1-и-VIP-2/План-VIP-1-и-VIP-2-с-коридорами.context.json'],
      'vip1Decision':'Latest common saved layout, bare column; three later proposals were not selected.',
      'vip2Decision':'Selected storage treatment, L sofa against high window wall, two poufs, table 1.40 × 0.80.',
      'display':'Removed completely from between the lower columns.',
      'people':{'countOnPlan':7,'view':'top','shoulderWidth':.5,'bodyDepth':.3},
      'pcPlaces':10,'conditionalPcReserve':2,'vipAreasApprox':[12,17],
      'confirmedExit63':VIP['exit63'],
      'geometryOrigin':'Upper left inner corner of room 86, x to right, y down. Coordinates use the v5 sketch frame.',
      'columns':[{'x':x,'y':y,'w':.41,'h':.41} for x,y in [(1.77,1.58),(5.05,1.58),(1.52,9.55),(5.05,9.55)]],
      'windowsApprox':{'rightWallY':[[.35,1.50],[2.45,4.60],[10.10,13.35]],'bottomWallX':[[2.55,4.18],[6.06,7.64]],'sillHeight':None},
      'vipGeometry':VIP,
      'sourceDimensions':{'room86Width':8.37,'room86Depth':5.18,'lowerWidth':9.86,'lowerLeftDepth':6.76,'lowerRightDepth':8.59,'columnSize':.41,'heightLabel':4.37},
      'drawnDimensions':detail_dimensions,
      'dimensionPolicy':'Only explicit source-plan dimensions are black. All coordinate-derived dimensions carry ≈ and blue text. Wall thickness symbolic. Not a measured construction drawing.',
      'dimensionCaveats':['Room 99 outline is schematic; recorded area 2.2 m² is not recalculated from the schematic rectangle.','The mark 5.64 is a source reference, not an opening width.','WC 89/90 dimensions apply to the combined schematic block, not each individual room.','Conditional PC reserve is not an approved layout; occupied-chair clearances are unverified.'],
      'files':{'detailSvg':'План-клуба-v6-с-размерами.svg','detailPng':'План-клуба-v6-с-размерами.png','sketchSvg':'План-клуба-v6-эскиз.svg','sketchPng':'План-клуба-v6-эскиз.png','html':'План-клуба-v6.html','source':'generate_v6.py'},
      'svgSha256':{'detail':hashlib.sha256(detailed_svg.encode()).hexdigest(),'sketch':hashlib.sha256(sketch_svg.encode()).hexdigest()}
    }
    (OUT/'План-клуба-v6.context.json').write_text(json.dumps(ctx,ensure_ascii=False,indent=2)+'\n')
    print('Saved v6 SVG sheets, HTML and context.')

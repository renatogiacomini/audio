#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A Máquina do Tempo do Áudio — v2.3 Portable
v2 + assets gráficos PNG integrados.
"""
import os, sys, math, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

MAX_SECONDS=15.0; INTERNAL_FS=48000; BYTES_PER_SAMPLE=2
RATES=[4000,6000,8000,12000,16000,24000,32000,48000]
RNG=np.random.default_rng(2026)
BG="#08141d"; PANEL="#0d1d28"; PANEL2="#102634"; TEXT="#f2eadb"; MUTED="#9eb1bd"
GOLD="#e2aa4f"; BLUE="#39aef2"; GREEN="#35b978"; RED="#c94b43"

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"

PROFILES={
"Fonógrafo":{"year":"1900","asset":"fonografo.png","low":180,"high":3500,"noise":.025,"drive":2.20,"clicks":.003,
"desc":"Reprodução mecânica: faixa estreita, ruído de superfície e distorção perceptível."},
"Disco 78 rpm":{"year":"1930","asset":"disco_78rpm.png","low":100,"high":5000,"noise":.018,"drive":1.75,"clicks":.0018,
"desc":"Maior extensão de frequências, ainda com ruído de superfície e limitações mecânicas."},
"Rádio AM":{"year":"1950","asset":"radio_am.png","low":120,"high":4500,"noise":.012,"drive":1.35,"clicks":.0002,
"desc":"Comunicação para as massas: faixa limitada, ruído perceptível e boa inteligibilidade de voz."},
"Rádio FM":{"year":"1970","asset":"radio_fm.png","low":40,"high":15000,"noise":.0025,"drive":1.08,"clicks":0,
"desc":"Faixa mais ampla e menor ruído, oferecendo reprodução musical muito superior ao AM."},
"Fita cassete":{"year":"1980","asset":"cassete.png","low":45,"high":14000,"noise":.0065,"drive":1.22,"clicks":0,
"desc":"Boa resposta de frequência, com hiss de fita e saturação suave."},
"CD":{"year":"1982","asset":"cd.png","low":20,"high":20000,"noise":0,"drive":1,"clicks":0,
"desc":"Áudio digital com ampla faixa e ruído muito baixo."},
"Original":{"year":"Hoje","asset":"digital.png","low":20,"high":20000,"noise":0,"drive":1,"clicks":0,
"desc":"Referência: o trecho carregado antes da simulação histórica."}
}

def normalize(x):
    x=np.asarray(x,dtype=float); p=np.max(np.abs(x)) if len(x) else 0
    return x*.92/p if p else x
def mono(x): return x if x.ndim==1 else np.mean(x,axis=1)
def resample_audio(x,f1,f2):
    if f1==f2:return x.copy()
    from math import gcd
    g=gcd(int(f1),int(f2)); return signal.resample_poly(x,f2//g,f1//g)
def bandlimit(x,fs,lo,hi):
    hi=min(hi,.95*fs/2); lo=min(max(lo,10),hi/2)
    sos=signal.butter(5,[lo,hi],btype="bandpass",fs=fs,output="sos")
    return signal.sosfiltfilt(sos,x)
def historical_effect(x,fs,p):
    y=bandlimit(x,fs,p["low"],p["high"])
    if p["drive"]>1:
        d=p["drive"]; y=np.tanh(d*y)/np.tanh(d)
    if p["noise"]>0:
        n=RNG.normal(size=len(y)); sos=signal.butter(2,1200,btype="highpass",fs=fs,output="sos")
        h=signal.sosfilt(sos,n); h/=max(np.std(h),1e-12); y+=p["noise"]*h
    if p["clicks"]>0:
        cnt=max(1,int(len(y)/fs*8*(p["clicks"]/.003)))
        for i in RNG.integers(0,len(y),cnt):
            w=min(int(.0015*fs),len(y)-i)
            if w>1:y[i:i+w]+=np.linspace(.35,0,w)
    return normalize(y)
def load_audio(path):
    ext=os.path.splitext(path)[1].lower()
    if ext not in (".wav",".mp3",".flac",".ogg"):
        raise RuntimeError("Use WAV, MP3, FLAC ou OGG.")

    # Primeiro tenta libsndfile/soundfile, inclusive para MP3 nas versões atuais.
    try:
        x,fs=sf.read(path,always_2d=False)
    except Exception:
        if ext != ".mp3":
            raise
        # Fallback portátil para MP3: FFmpeg fornecido pelo pacote imageio-ffmpeg.
        try:
            from pydub import AudioSegment
            import imageio_ffmpeg
            AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
            s=AudioSegment.from_file(path).set_channels(1)
            fs=s.frame_rate
            x=np.array(s.get_array_of_samples(),dtype=float)/(1<<(8*s.sample_width-1))
        except Exception as e:
            raise RuntimeError("Não foi possível abrir o arquivo MP3.") from e

    x=normalize(mono(np.asarray(x)))[:int(MAX_SECONDS*fs)]
    return normalize(resample_audio(x,int(fs),INTERNAL_FS)),INTERNAL_FS

class Knob(tk.Canvas):
    def __init__(self,master,command=None):
        super().__init__(master,width=235,height=235,bg=PANEL,highlightthickness=0)
        self.command=command; self.index=3
        self.bind("<Button-1>",self.click); self.bind("<B1-Motion>",self.click); self.draw()
    def click(self,e):
        a=(math.degrees(math.atan2(e.y-117,e.x-117))+360)%360
        if a<40:a+=360
        a=max(140,min(400,a)); self.index=int(round((a-140)/260*(len(RATES)-1)))
        self.draw()
        if self.command:self.command(RATES[self.index])
    def draw(self):
        self.delete("all"); c=117
        self.create_oval(27,27,207,207,fill="#172832",outline=GOLD,width=3)
        self.create_oval(45,45,189,189,fill="#59636a",outline="#b8c0c5",width=2)
        for i in range(len(RATES)):
            a=math.radians(140+i*260/(len(RATES)-1))
            self.create_line(c+90*math.cos(a),c+90*math.sin(a),c+102*math.cos(a),c+102*math.sin(a),fill=TEXT,width=2)
        a=math.radians(140+self.index*260/(len(RATES)-1))
        self.create_line(c,c,c+58*math.cos(a),c+58*math.sin(a),fill=BLUE,width=7)
        self.create_oval(c-9,c-9,c+9,c+9,fill="#ddd",outline="#222")

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("A Máquina do Tempo do Áudio — v2.3 Portable")
        self.geometry("1500x920"); self.minsize(1200,780); self.configure(bg=BG)
        self.audio=None; self.processed=None; self.fs=INTERNAL_FS; self.selected="Rádio AM"; self.rate=12000
        self.photos_small={}; self.photos_large={}
        self.load_assets(); self.make_ui(); self.select_era("Rádio AM")
    def load_assets(self):
        for name,p in PROFILES.items():
            im=Image.open(ASSET_DIR/p["asset"]).convert("RGBA")
            s=im.copy(); s.thumbnail((135,92),Image.Resampling.LANCZOS)
            l=im.copy(); l.thumbnail((350,230),Image.Resampling.LANCZOS)
            self.photos_small[name]=ImageTk.PhotoImage(s); self.photos_large[name]=ImageTk.PhotoImage(l)
    def lab(self,parent,text,size=11,bold=False,fg=TEXT,bg=None,**kw):
        return tk.Label(parent,text=text,font=("Helvetica",size,"bold" if bold else "normal"),fg=fg,bg=bg or parent.cget("bg"),**kw)
    def btn(self, parent, text, cmd, bg="#174c6b", width=16):
        """Botão customizado, com cores consistentes também no macOS."""
        frame = tk.Frame(
            parent,
            bg="#314956",
            padx=1,
            pady=1
        )

        button = tk.Label(
            frame,
            text=text,
            bg=bg,
            fg="white",
            padx=12,
            pady=9,
            width=width,
            font=("Helvetica", 11, "bold"),
            cursor="hand2"
        )
        button.pack(fill="both", expand=True)

        def on_click(event):
            cmd()

        def on_enter(event):
            button.configure(bg=self.lighten_color(bg))
            frame.configure(bg=GOLD)

        def on_leave(event):
            button.configure(bg=bg)
            frame.configure(bg="#314956")

        button.bind("<Button-1>", on_click)
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

        return frame

    def lighten_color(self, color, factor=1.25):
        """Clareia uma cor hexadecimal para o efeito hover."""
        color = color.lstrip("#")
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))

        return f"#{r:02x}{g:02x}{b:02x}"
    def make_ui(self):
        h=tk.Frame(self,bg="#18232a"); h.pack(fill="x")
        self.lab(h,"A MÁQUINA DO TEMPO DO ÁUDIO",27,True,fg="#f3cf8b",bg="#18232a").pack(pady=(8,0))
        self.lab(h,"Uma viagem pela história da reprodução sonora",14,fg="#7bd0ff",bg="#18232a").pack(pady=(0,7))
        body=tk.Frame(self,bg=BG); body.pack(fill="both",expand=True,padx=8,pady=7)
        left=tk.Frame(body,bg=BG); left.pack(side="left",fill="both",expand=True)
        right=tk.Frame(body,bg=PANEL,width=330); right.pack(side="right",fill="y",padx=(7,0)); right.pack_propagate(False)

        src=tk.Frame(left,bg=PANEL); src.pack(fill="x",pady=(0,6))
        self.lab(src,"1. ESCOLHA UM ÁUDIO",14,True,bg=PANEL).pack(anchor="w",padx=10,pady=(6,2))
        r=tk.Frame(src,bg=PANEL); r.pack(fill="x",padx=8,pady=(0,8))
        self.btn(r,"🎙 Gravar voz",self.record,RED).pack(side="left",padx=4)
        self.btn(r,"♫ Carregar música",self.open_audio,"#17608b").pack(side="left",padx=4)
        self.btn(r,"▶ Ouvir original",self.play_original,"#236448").pack(side="left",padx=4)
        self.status=self.lab(r,"Nenhum áudio carregado",10,fg=MUTED,bg=PANEL); self.status.pack(side="left",padx=12)

        eras=tk.Frame(left,bg=PANEL); eras.pack(fill="x",pady=(0,6))
        self.lab(eras,"2. VIAJE NO TEMPO",14,True,bg=PANEL).pack(anchor="w",padx=10,pady=(6,3))
        cards=tk.Frame(eras,bg=PANEL); cards.pack(fill="x",padx=6,pady=(0,6))
        self.cards={}
        for name,p in PROFILES.items():
            c=tk.Frame(cards,bg=PANEL2,highlightthickness=2,highlightbackground="#344b59")
            c.pack(side="left",fill="both",expand=True,padx=2)
            pic=tk.Label(c,image=self.photos_small[name],bg=PANEL2,cursor="hand2"); pic.pack(pady=(4,0))
            txt=self.lab(c,f"{p['year']}\n{name}",10,True,bg=PANEL2,justify="center",cursor="hand2"); txt.pack(pady=(0,4))
            for w in (c,pic,txt):w.bind("<Button-1>",lambda e,n=name:self.select_era(n))
            self.cards[name]=(c,pic,txt)

        detail=tk.Frame(left,bg=PANEL); detail.pack(fill="x",pady=(0,6))
        self.bigpic=tk.Label(detail,bg=PANEL); self.bigpic.pack(side="left",padx=12,pady=8)
        info=tk.Frame(detail,bg=PANEL); info.pack(side="left",fill="both",expand=True,pady=8)
        self.title2=self.lab(info,"",19,True,fg="#f3cf8b",bg=PANEL); self.title2.pack(anchor="w")
        self.desc=self.lab(info,"",11,bg=PANEL,wraplength=520,justify="left"); self.desc.pack(anchor="w",pady=4)
        self.tech=self.lab(info,"",10,fg="#e9c58d",bg=PANEL,justify="left"); self.tech.pack(anchor="w",pady=3)
        br=tk.Frame(info,bg=PANEL); br.pack(anchor="w",pady=5)
        self.btn(br,"▶ Ouvir época",self.play_era,"#23714e").pack(side="left",padx=3)
        self.btn(br,"A/B Comparar",self.ab_compare,"#1d5f88").pack(side="left",padx=3)

        gf=tk.Frame(left,bg=PANEL); gf.pack(fill="both",expand=True)
        self.fig=Figure(figsize=(9.5,3.6),dpi=100,facecolor=PANEL); self.ax1=self.fig.add_subplot(121); self.ax2=self.fig.add_subplot(122)
        self.canvas=FigureCanvasTkAgg(self.fig,master=gf); self.canvas.get_tk_widget().pack(fill="both",expand=True,padx=5,pady=5)

        self.lab(right,"MODO ENGENHEIRO",19,True,fg="#f3cf8b",bg=PANEL).pack(pady=(12,0))
        self.lab(right,"Projete seu sistema de áudio digital",10,fg=MUTED,bg=PANEL).pack()
        self.lab(right,"Medições por segundo",13,True,bg=PANEL).pack(pady=(12,0))
        self.knob=Knob(right,self.set_rate); self.knob.pack()
        self.rd=self.lab(right,"12.000 medições / segundo",14,True,fg=BLUE,bg=PANEL); self.rd.pack()
        box=tk.Frame(right,bg=PANEL2,highlightthickness=1,highlightbackground="#416375"); box.pack(fill="x",padx=10,pady=10)
        self.lab(box,"CUSTO DE ARMAZENAMENTO",12,True,bg=PANEL2).pack(anchor="w",padx=10,pady=(8,0))
        self.lab(box,"2 bytes por medição",9,fg=MUTED,bg=PANEL2).pack(anchor="w",padx=10)
        self.cost=self.lab(box,"",11,bg=PANEL2,justify="left"); self.cost.pack(anchor="w",padx=10,pady=8)
        self.btn(right,"▶ Ouvir minha escolha",self.play_engineer,"#17608b",23).pack(pady=5)
        mission=tk.Frame(right,bg="#15232b",highlightthickness=1,highlightbackground=GOLD); mission.pack(fill="x",padx=10,pady=8)
        self.lab(mission,"MISSÃO",14,True,fg="#f3cf8b",bg="#15232b").pack(anchor="w",padx=10,pady=(8,2))
        self.lab(mission,"Armazene 1 hora de áudio usando\nno máximo 100 MB.\nO áudio ainda é adequado?",10,bg="#15232b",justify="left").pack(anchor="w",padx=10)
        self.fit=self.lab(mission,"",13,True,bg="#15232b"); self.fit.pack(pady=8)
        self.set_rate(12000)
    def require(self):
        if self.audio is None: messagebox.showinfo("Máquina do Tempo","Carregue uma música ou grave sua voz primeiro."); return False
        return True
    def open_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Áudio","*.wav *.mp3 *.flac *.ogg"),("Todos","*.*")])
        if not p:return
        try:self.audio,self.fs=load_audio(p); self.status.config(text=f"{os.path.basename(p)} — primeiros {len(self.audio)/self.fs:.1f} s"); self.select_era(self.selected)
        except Exception as e:messagebox.showerror("Erro",str(e))
    def record(self):
        try:
            self.status.config(text="Gravando 15 segundos..."); self.update()
            r=sd.rec(int(MAX_SECONDS*self.fs),samplerate=self.fs,channels=1,dtype="float64"); sd.wait()
            self.audio=normalize(r[:,0]); self.status.config(text="Gravação de voz — 15 s"); self.select_era(self.selected)
        except Exception as e:messagebox.showerror("Microfone",str(e))
    def select_era(self,name):
        self.selected=name;p=PROFILES[name]
        for n,(c,pic,txt) in self.cards.items():
            c.config(highlightbackground=GOLD if n==name else "#344b59",highlightthickness=3 if n==name else 2)
            txt.config(fg="#ffd77b" if n==name else TEXT)
        self.bigpic.config(image=self.photos_large[name])
        self.title2.config(text=f"{name.upper()} — {p['year']}")
        self.desc.config(text=p["desc"])
        self.tech.config(text=f"Faixa didática: {p['low']} Hz – {p['high']/1000:.1f} kHz\nRuído relativo: {p['noise']:.4f}   Distorção: {p['drive']:.2f}")
        if self.audio is not None:self.processed=historical_effect(self.audio,self.fs,p);self.draw()
    def play_original(self):
        if self.require():sd.stop();sd.play(self.audio,self.fs)
    def play_era(self):
        if self.require():self.select_era(self.selected);sd.stop();sd.play(self.processed,self.fs)
    def ab_compare(self):
        if not self.require():return
        self.select_era(self.selected);n=min(len(self.audio),4*self.fs);pause=np.zeros(int(.35*self.fs))
        sd.stop();sd.play(np.concatenate([self.audio[:n],pause,self.processed[:n]]),self.fs)
    def set_rate(self,r):
        self.rate=int(r);self.rd.config(text=f"{r:,} medições / segundo".replace(",","."))
        b=r*BYTES_PER_SAMPLE; m=b*60/1e6; h=b*3600/1e6
        self.cost.config(text=f"Dados por segundo:   {b/1000:6.1f} kB\nDados por minuto:    {m:6.2f} MB\nMúsica de 4 min:     {m*4:6.2f} MB\nUma hora de áudio:   {h:6.1f} MB")
        ok=h<=100;self.fit.config(text="✓ CABE EM 100 MB" if ok else "✗ NÃO CABE EM 100 MB",fg=GREEN if ok else RED)
    def play_engineer(self):
        if not self.require():return
        lo=resample_audio(self.audio,self.fs,self.rate);back=normalize(resample_audio(lo,self.rate,self.fs));sd.stop();sd.play(back,self.fs)
    def draw(self):
        for ax in (self.ax1,self.ax2):
            ax.clear();ax.set_facecolor("#07121a");ax.tick_params(colors="#cbd5da",labelsize=8)
            for s in ax.spines.values():s.set_color("#506775")
            ax.grid(True,alpha=.18)
        step=max(1,len(self.audio)//6000);t=np.arange(0,len(self.audio),step)/self.fs
        self.ax1.plot(t,self.audio[::step],label="Original",lw=.7);self.ax1.plot(t,self.processed[::step],label=self.selected,lw=.7)
        self.ax1.set_title("FORMA DE ONDA",color=TEXT,fontsize=10);self.ax1.set_xlabel("Tempo (s)",color=MUTED);self.ax1.legend(fontsize=7)
        n=min(len(self.audio),4*self.fs);f,a=signal.welch(self.audio[:n],self.fs,nperseg=4096);_,b=signal.welch(self.processed[:n],self.fs,nperseg=4096)
        self.ax2.semilogx(f[1:],10*np.log10(a[1:]+1e-12),label="Original");self.ax2.semilogx(f[1:],10*np.log10(b[1:]+1e-12),label=self.selected)
        self.ax2.set_xlim(20,24000);self.ax2.set_title("ESPECTRO DE FREQUÊNCIAS",color=TEXT,fontsize=10);self.ax2.set_xlabel("Frequência (Hz)",color=MUTED);self.ax2.legend(fontsize=7)
        self.fig.tight_layout(pad=2);self.canvas.draw()
if __name__=="__main__":App().mainloop()

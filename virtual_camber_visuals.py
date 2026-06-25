############################################################################
#                     VIRTUAL CAMBER/CFT TRANSFORMATION                    #
############################################################################
import numpy as np
# import matplotlib.pyplot as mpl
# m     =   maximum camber/chord
# p     =   location of max camber/chord
# t     =   maximum thickness/chord
def naca_plot(xxxx):
    # get info from name
    m=int(xxxx[0])/100
    p=int(xxxx[1])/10
    t=int(xxxx[2:])/100
    x,y_c,dy_c=np.linspace(0,1,500),np.zeros(500),np.zeros(500)
    
    # symmetrical shape
    y_t=5*t*(0.2969*np.sqrt(x)-0.126*x-0.3516*x**2+0.2843*x**3-0.1036*x**4)
    
    # chord line
    x_ch=np.linspace(0,1,500)
    y_ch=np.zeros_like(x_ch)
    
    # mean camber
    if p != 0:
        for i, x_i in enumerate(x):
            if x_i<=p: 
                y_c[i]=(m/p**2)*(2*p*x_i-x_i**2)
                dy_c[i]=(2*m/p)*(p-x_i)
            elif x_i>p and x_i<=1: 
                y_c[i]=(m/(1-p)**2)*((1-2*p)+2*p*x_i-x_i**2)
                dy_c[i]=(2*m/(1-p)**2)*(p-x_i)
            
    theta=np.arctan(dy_c)

    x_L,x_U=x+y_t*np.sin(theta),x-y_t*np.sin(theta)
    y_L,y_U=y_c-y_t*np.cos(theta),y_c+y_t*np.cos(theta)
    
    x_plot,y_plot=[x_L,x_U],[y_L,y_U]
    return x_plot,y_plot,(x,y_c),(x_ch,y_ch)

def aoa(theta,tsr): return np.arctan(np.sin(theta)/(tsr+np.cos(theta)))

# R     =   distance to turbine center, mounted at c/4
# tsr   =   tip-speed ratio
def blade_transform(x_plot,y_plot,cR_ratio,tsr,theta):
    x_v,y_v=[],[]
    R,theta=1/cR_ratio,theta*np.pi/180
    for x_s,y_s in zip(x_plot,y_plot):
        # distance from blade point to offset center
        r=np.sqrt((x_s+R/tsr*np.sin(theta))**2+(y_s+R+R/tsr*np.cos(theta))**2) 
        
        # angular position on streamline
        phi=np.pi/2-aoa(theta,tsr)-np.arccos((x_s+R/tsr*np.sin(theta))/r)
        
        # reference streamline
        R_c=R/tsr*np.sqrt(1+2*tsr*np.cos(theta)+tsr**2)
    
        #conformal map: polar to virtal (rectilinear)
        x_v.append(phi*R_c)
        y_v.append(r-R_c)
    
    return x_v,y_v

############################################################################
#                       GUI/Interactive App Code                           #
############################################################################
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLineEdit, QGroupBox, QSlider, QLabel, QHBoxLayout, QCheckBox, QPushButton, QFileDialog
from PySide6.QtCore import Qt, QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation, PillowWriter

class Controls(QWidget):
    def __init__(self, on_change):
        super().__init__()
        self.setWindowTitle("Inputs")

        #####################################
        # set up variables 
        #####################################
        self.naca_profile = QLineEdit("0018"); self.naca_profile.editingFinished.connect(on_change)
        
        self.tsr = QDoubleSpinBox(); self.tsr.setRange(0,100000); self.tsr.setDecimals(2); self.tsr.setSingleStep(0.01)
        self.tsr.setValue(1.9); self.tsr.valueChanged.connect(on_change)
        
        self.cR_ratio = QDoubleSpinBox(); self.cR_ratio.setRange(0,1); self.cR_ratio.setDecimals(2); self.cR_ratio.setSingleStep(0.01)
        self.cR_ratio.setValue(0.49); self.cR_ratio.valueChanged.connect(on_change)
        
        self.theta = QSlider(Qt.Horizontal); self.theta.setRange(0,360); self.theta.setSingleStep(1)
        self.theta.setTickPosition(QSlider.TicksBelow); self.theta.setTickInterval(90); self.theta.setValue(0); self.theta.valueChanged.connect(on_change)
        ticks = QHBoxLayout()
        for i, t in enumerate([0, 90, 180, 270, 360]):
            lbl = QLabel(str(t))
            lbl.setAlignment(Qt.AlignLeft if t == 0 else
                            Qt.AlignRight if t == 360 else Qt.AlignCenter)
            ticks.addWidget(lbl, 1)

        theta_box = QVBoxLayout()
        theta_box.addWidget(self.theta)
        theta_box.addLayout(ticks)
        
        self.show_camber = QCheckBox(); self.show_camber.setChecked(True); self.show_camber.toggled.connect(on_change)
        self.show_chord = QCheckBox(); self.show_chord.setChecked(True); self.show_chord.toggled.connect(on_change)
        
        self.animate = QCheckBox(); self.animate.setChecked(False)
        
        self.show_legend = QCheckBox(); self.show_legend.setChecked(True); self.show_legend.toggled.connect(on_change)
        
        self.save_img_btn = QPushButton("Save image")
        self.save_anim_btn = QPushButton("Save animation")


        ##################################
        # establish inputs
        ##################################
        form = QFormLayout()
        form.addRow("NACA XXXX", self.naca_profile)
        form.addRow('Tip-Speed Ratio', self.tsr)
        form.addRow('Chord-Radius Ratio', self.cR_ratio)
        form.addRow('Theta', theta_box)
        form.addRow("Camber line", self.show_camber)
        form.addRow("Chord line", self.show_chord)
        form.addRow("Animate angle", self.animate)
        form.addRow("Legend", self.show_legend)
        form.addRow(self.save_img_btn)
        form.addRow(self.save_anim_btn)
        box = QGroupBox("Inputs"); box.setLayout(form)
        root = QVBoxLayout(self); root.addWidget(box); root.addStretch()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plot")

        self.fig = Figure(figsize=(12, 5))
        self.canvas = FigureCanvas(self.fig)
        self.ax  = self.fig.add_subplot(1, 2, 1)  
        self.ax2 = self.fig.add_subplot(1, 2, 2)   
        root = QVBoxLayout(self); root.addWidget(self.canvas)

        self.ctrl = Controls(self.replot)
        self.ctrl.show()

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.step_theta)
        self.ctrl.animate.toggled.connect(lambda on: self.timer.start() if on else self.timer.stop())
        if self.ctrl.animate.isChecked():
            self.timer.start()
        self.ctrl.save_img_btn.clicked.connect(self.save_image)
        self.ctrl.save_anim_btn.clicked.connect(self.save_animation)
        self.replot()

    def step_theta(self):
                dtheta=self.ctrl.theta
                dtheta.setValue((dtheta.value()+1)%361)
    
    def replot(self):
        # create inital blade profile
        naca_profile = self.ctrl.naca_profile.text()
        (x_l, x_u), (y_l, y_u), (x_c,y_c), (x_ch,y_ch) = naca_plot(naca_profile)
        
        # get cft conditions
        tsr=self.ctrl.tsr.value()
        cR_ratio=self.ctrl.cR_ratio.value()
        theta=self.ctrl.theta.value()
        
        # perform virtual camber transformation
        (x_v_l,x_v_u),(y_v_l,y_v_u)=blade_transform([x_l,x_u],[y_l,y_u],cR_ratio,tsr,theta)
        
        self.fig.suptitle(f'$\lambda=${tsr}, $c/R=${cR_ratio}')
        
        self.ax.clear()                
        self.ax.plot(x_v_l, y_v_l,color='black'); self.ax.plot(x_v_u, y_v_u,label='NACA 0018',color='black')
        self.ax.axis('equal'); self.ax.grid(alpha=.3); self.ax.set_xlabel('$x/c$'); self.ax.set_ylabel('$y/c$',rotation=0)
        
        # toggle camber line
        if self.ctrl.show_camber.isChecked():
            [x_c_v],[y_c_v]=blade_transform([x_c],[y_c],cR_ratio,tsr,theta)
            self.ax.plot(x_c_v, y_c_v, '--', lw=1.5,label='Camber Line')
        # toggle chord line
        if self.ctrl.show_chord.isChecked():
            # transformed chord
            [x_ch_v],[y_ch_v]=blade_transform([x_ch],[y_ch],cR_ratio,tsr,theta)
            self.ax.plot(x_ch_v, y_ch_v, '--', lw=0.5,label='Transformed Chord Line')
            # new chord
            self.ax.plot([x_ch_v[0], x_ch_v[-1]],[y_ch_v[0], y_ch_v[-1]], '-', lw=1, color='gray',label='Virtual Chord Line')
            print(f'Virtual chord line length: {np.sqrt((x_ch_v[0]-x_ch_v[-1])**2+(y_ch_v[0]-y_ch_v[-1])**2)}') # should be less than 1
        # toggle legend
        if self.ctrl.show_legend.isChecked():
            self.ax.legend()
        
        # plot theta vs. aoa
        self.ax2.clear()
        theta_vals_deg = np.linspace(0, 360, 361)
        theta_vals_rad = np.deg2rad(theta_vals_deg)
        aoa_vals = np.degrees(aoa(theta_vals_rad, tsr))   # aoa() returns radians
        self.ax2.plot(theta_vals_deg, aoa_vals)
        self.ax2.set_xlabel(r'$\theta$ (deg)'); self.ax2.set_ylabel(r'$\alpha$ (deg)')
        self.ax2.grid(alpha=.3)
        self.ax2.plot(theta, np.degrees(aoa(np.deg2rad(theta), tsr)), 'o', color='red')

        self.ax.set_xlim(-0.1,1.1); self.ax.set_ylim(-1,1)        
        self.canvas.draw_idle()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save image", "blade.png",
                                              "Images (*.png *.pdf *.svg)")
        if path:
            self.fig.savefig(path, dpi=200, bbox_inches='tight')

    def save_animation(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save animation", "blade.gif", "GIF (*.gif)")
        if not path:
            return
        was_running = self.timer.isActive()
        self.timer.stop()

        def update(deg):
            self.ctrl.theta.setValue(deg)
            return []

        anim = FuncAnimation(self.fig, update, frames=range(0, 361, 2),
                             interval=1000/30, blit=False)
        anim.save(path, writer=PillowWriter(fps=30))

        if was_running:
            self.timer.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = App(); w.show()
    sys.exit(app.exec())
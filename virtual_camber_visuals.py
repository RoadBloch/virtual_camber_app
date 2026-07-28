############################################################################
#                     VIRTUAL CAMBER/CFT TRANSFORMATION                    #
############################################################################
import numpy as np
# import matplotlib.pyplot as mpl
# m     =   maximum camber/chord
# p     =   location of max camber/chord
# t     =   maximum thickness/chord
def naca_plot(xxxx,center=[0.25,0]):
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

    x_L,x_U=x+y_t*np.sin(theta)-center[0],x-y_t*np.sin(theta)-center[0]
    y_L,y_U=y_c-y_t*np.cos(theta),y_c+y_t*np.cos(theta)
    
    x_plot,y_plot=[x_L,x_U],[y_L,y_U]
    return x_plot,y_plot,(x-center[0],y_c),(x_ch-center[0],y_ch)

def aoa(theta,tsr): return np.arctan(np.sin(theta)/(tsr+np.cos(theta)))

# R     =   distance to turbine center, mounted at c/4
# tsr   =   tip-speed ratio
def blade_transform(x_plot,y_plot,cR_ratio,tsr,theta):
    x_v,y_v =   [],[]
    R,theta =   1/cR_ratio,theta*np.pi/180
    for x_s,y_s in zip(x_plot,y_plot):
        # distance from blade point to offset center
        r   =   np.sqrt((x_s+R/tsr*np.sin(theta))**2+(y_s+R+R/tsr*np.cos(theta))**2) 
        
        # angular position on streamline
        phi =   np.pi/2-aoa(theta,tsr)-np.arccos((x_s+R/tsr*np.sin(theta))/r)
        
        # reference streamline
        R_c =   R/tsr*np.sqrt(1+2*tsr*np.cos(theta)+tsr**2)
    
        #conformal map: polar to virtal (rectilinear)
        x_v.append(phi*R_c)
        y_v.append(r-R_c)
    
    return x_v,y_v

# R     =   distance to turbine center, mounted at c/4
# tsr   =   tip-speed ratio
def plot_streamline(theta,R,tsr,n_rings=6):
    theta   =   theta*np.pi/180
    center  =   (0,-R/tsr)   # streamline center, offset from turbine center (matches R_c in blade_transform)

    # blade mounted at quarter-chord, radius R from turbine center
    x_mount =   -R*np.sin(theta)
    y_mount =   R*np.cos(theta)
    r_blade =   np.sqrt(x_mount**2+(y_mount-center[1])**2)

    phi     =   np.linspace(0,2*np.pi,200)
    orbit   =   (R*np.sin(phi),R*np.cos(phi))                             # blade's circular path
    blade_stream = (center[0]+r_blade*np.cos(phi),center[1]+r_blade*np.sin(phi))

    rings = [(center[0]+r*np.cos(phi),center[1]+r*np.sin(phi))
             for r in np.linspace(r_blade/n_rings,r_blade*2,n_rings)]

    return (x_mount,y_mount),center,orbit,blade_stream,rings

# rotate/translate a blade (centered at c/4) to its physical position on the turbine orbit
def orient_blade(x_plot,y_plot,x_mount,y_mount,theta):
    theta = theta*np.pi/180
    x_r,y_r = [],[]
    for x_s,y_s in zip(x_plot,y_plot):
        x_r.append(x_s*np.cos(theta)-y_s*np.sin(theta)+x_mount)
        y_r.append(x_s*np.sin(theta)+y_s*np.cos(theta)+y_mount)
    return x_r,y_r


############################################################################
#                       GUI/Interactive App Code                           #
############################################################################
import sys
import matplotlib
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLineEdit, QGroupBox, QSlider, QLabel, QHBoxLayout, QCheckBox, QPushButton, QFileDialog, QDialog, QComboBox, QColorDialog
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation, PillowWriter

# graph colors: (key, label, default hex)
COLOR_SPECS = [
    ('blade_outline', 'Blade outline',      '#000000'),
    ('camber_line',   'Camber line',        '#1f77b4'),
    ('chord_line',    'Chord lines',        '#7f7f7f'),
    ('aoa_line',      'AoA curve',          '#1f77b4'),
    ('aoa_point',     'AoA marker',         '#ff0000'),
    ('rings',         'Orbit rings',        '#7f7f7f'),
    ('orbit',         'Blade orbit path',   '#000000'),
    ('streamline',    'Streamline',         '#1f77b4'),
    ('blade_ax3',     'Blade (orbit plot)', '#ff0000'),
]
DEFAULT_COLORS = {key: hexcolor for key, _, hexcolor in COLOR_SPECS}
FONT_CHOICES = ['DejaVu Sans', 'Calibri', 'Arial', 'Times New Roman', 'Courier New']


class GraphSettingsDialog(QDialog):
    def __init__(self, ctrl):
        super().__init__()
        self.setWindowTitle("Graph Settings")
        self.ctrl = ctrl
        self.color_buttons = {}

        layout = QVBoxLayout(self)

        font_group = QGroupBox("Font")
        font_form = QFormLayout()
        self.font_combo = QComboBox(); self.font_combo.addItems(FONT_CHOICES)
        self.font_combo.setCurrentText(ctrl.font_family)
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        font_form.addRow("Family", self.font_combo)

        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(6, 30); self.font_size_spin.setSingleStep(0.5)
        self.font_size_spin.setValue(ctrl.font_size)
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)
        font_form.addRow("Font size", self.font_size_spin)
        font_group.setLayout(font_form)
        layout.addWidget(font_group)

        scale_group = QGroupBox("Scale")
        scale_form = QFormLayout()
        self.zoom_spin = QDoubleSpinBox()
        self.zoom_spin.setRange(0.2, 5.0); self.zoom_spin.setSingleStep(0.1)
        self.zoom_spin.setValue(ctrl.plot_scale)
        self.zoom_spin.valueChanged.connect(self.on_zoom_changed)
        scale_form.addRow("Zoom (blade/orbit view)", self.zoom_spin)
        scale_group.setLayout(scale_form)
        layout.addWidget(scale_group)

        color_group = QGroupBox("Colors")
        color_form = QFormLayout()
        for key, label, _ in COLOR_SPECS:
            btn = QPushButton(); btn.setFixedWidth(60)
            self._style_swatch(btn, ctrl.colors[key])
            btn.clicked.connect(lambda checked=False, k=key, b=btn: self.pick_color(k, b))
            self.color_buttons[key] = btn
            color_form.addRow(label, btn)
        color_group.setLayout(color_form)
        layout.addWidget(color_group)

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        layout.addWidget(reset_btn)

    def _style_swatch(self, btn, hex_color):
        btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #888;")

    def on_font_changed(self, name):
        self.ctrl.font_family = name
        self.ctrl.on_change()

    def on_font_size_changed(self, value):
        self.ctrl.font_size = value
        self.ctrl.on_change()

    def on_zoom_changed(self, value):
        self.ctrl.plot_scale = value
        self.ctrl.on_change()

    def pick_color(self, key, btn):
        color = QColorDialog.getColor(QColor(self.ctrl.colors[key]), self, "Pick color")
        if color.isValid():
            self.ctrl.colors[key] = color.name()
            self._style_swatch(btn, color.name())
            self.ctrl.on_change()

    def reset_defaults(self):
        self.ctrl.colors = DEFAULT_COLORS.copy()
        self.ctrl.font_family = 'DejaVu Sans'
        self.ctrl.font_size = 10.0
        self.ctrl.plot_scale = 1.0
        for key, btn in self.color_buttons.items():
            self._style_swatch(btn, self.ctrl.colors[key])
        self.font_combo.setCurrentText(self.ctrl.font_family)
        self.font_size_spin.setValue(self.ctrl.font_size)
        self.zoom_spin.setValue(self.ctrl.plot_scale)
        self.ctrl.on_change()


class Controls(QWidget):
    def __init__(self, on_change):
        super().__init__()
        self.setWindowTitle("Inputs")
        self.on_change = on_change

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

        self.show_grid = QCheckBox(); self.show_grid.setChecked(True); self.show_grid.toggled.connect(on_change)

        self.font_family = 'DejaVu Sans'
        self.font_size = 10.0
        self.plot_scale = 1.0
        self.colors = DEFAULT_COLORS.copy()
        self.settings_dialog = GraphSettingsDialog(self)
        self.settings_btn = QPushButton("Graph Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.show)

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
        form.addRow("Grid", self.show_grid)
        form.addRow(self.settings_btn)
        form.addRow(self.save_img_btn)
        form.addRow(self.save_anim_btn)
        box = QGroupBox("Inputs"); box.setLayout(form)
        root = QVBoxLayout(self); root.addWidget(box); root.addStretch()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plot")

        self.fig = Figure(figsize=(15, 6), layout='compressed')
        self.canvas = FigureCanvas(self.fig)
        self.ax  = self.fig.add_subplot(1, 3, 1)
        self.ax2 = self.fig.add_subplot(1, 3, 2)
        self.ax3 = self.fig.add_subplot(1, 3, 3)   # reserved for streamwise plot
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
        matplotlib.rcParams['font.family'] = self.ctrl.font_family
        matplotlib.rcParams['font.size'] = self.ctrl.font_size
        colors = self.ctrl.colors

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
        self.ax.plot(x_v_l, y_v_l,color=colors['blade_outline']); self.ax.plot(x_v_u, y_v_u,label='NACA 0018',color=colors['blade_outline'])
        self.ax.set_aspect('equal', adjustable='datalim'); self.ax.set_box_aspect(1)
        self.ax.set_xlim(-0.5, 1); self.ax.set_xlabel('$x/c$'); self.ax.set_ylabel('$y/c$',rotation=0)
        
        # toggle camber line
        if self.ctrl.show_camber.isChecked():
            [x_c_v],[y_c_v]=blade_transform([x_c],[y_c],cR_ratio,tsr,theta)
            self.ax.plot(x_c_v, y_c_v, '--', lw=1.5,label='Camber Line',color=colors['camber_line'])
        # toggle chord line
        if self.ctrl.show_chord.isChecked():
            # transformed chord
            [x_ch_v],[y_ch_v]=blade_transform([x_ch],[y_ch],cR_ratio,tsr,theta)
            self.ax.plot(x_ch_v, y_ch_v, '--', lw=0.5,label='Transformed Chord Line',color=colors['chord_line'])
            # new chord
            self.ax.plot([x_ch_v[0], x_ch_v[-1]],[y_ch_v[0], y_ch_v[-1]], '-', lw=1, color=colors['chord_line'],label='Virtual Chord Line')
            print(f'Virtual chord line length: {np.sqrt((x_ch_v[0]-x_ch_v[-1])**2+(y_ch_v[0]-y_ch_v[-1])**2)}') # should be less than 1
        # toggle legend
        if self.ctrl.show_legend.isChecked():
            self.ax.legend()
        
        # plot theta vs. aoa
        self.ax2.clear()
        theta_vals_deg = np.linspace(0, 360, 361)
        theta_vals_rad = np.deg2rad(theta_vals_deg)
        aoa_vals = np.degrees(aoa(theta_vals_rad, tsr))   # aoa() returns radians
        self.ax2.plot(theta_vals_deg, aoa_vals, color=colors['aoa_line'])
        self.ax2.set_xlabel(r'$\theta$ (deg)'); self.ax2.set_ylabel(r'$\alpha$ (deg)')
        self.ax2.set_xticks([0, 90, 180, 270, 360])
        self.ax2.plot(theta, np.degrees(aoa(np.deg2rad(theta), tsr)), 'o', color=colors['aoa_point'])

        # turbine-blade path
        self.ax3.clear()
        (x_mount,y_mount),center,(x_orbit,y_orbit),(x_bs,y_bs),rings = plot_streamline(theta,1/cR_ratio,tsr)
        for x_r,y_r in rings:
            self.ax3.plot(x_r,y_r,color=colors['rings'],lw=0.5,alpha=0.5)
        self.ax3.plot(x_orbit,y_orbit,'--',color=colors['orbit'],lw=1,label='Blade orbit')
        self.ax3.plot(x_bs,y_bs,color=colors['streamline'],lw=1.5,label='Streamline through blade')
        self.ax3.plot(center[0],center[1],'x',color=colors['streamline'])
        x_b,y_b = orient_blade([x_l,x_u],[y_l,y_u],x_mount,y_mount,theta)
        self.ax3.plot(x_b[0],y_b[0],color=colors['blade_ax3']); self.ax3.plot(x_b[1],y_b[1],color=colors['blade_ax3'],label='Blade')

        # fixed, theta-independent view so it doesn't jump as theta changes.
        # bounded tightly to the orbit/blade/streamline (not the outer decorative rings,
        # which may clip at the frame edge), and re-centered on their bounding box
        # instead of the origin so the square crop carries minimal dead space.
        R = 1/cR_ratio
        R_eff = R+1               # orbit radius plus a generous margin for blade overhang
        r_blade_max = R*(1+1/tsr) # max streamline radius, over all theta
        center_y = center[1]
        xmin, xmax = -max(R_eff, r_blade_max), max(R_eff, r_blade_max)
        ymin = min(-R_eff, center_y-r_blade_max)
        ymax = max(R_eff, center_y+r_blade_max)
        side = 1.1*max(xmax-xmin, ymax-ymin)*self.ctrl.plot_scale
        cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
        self.ax3.set_xlim(cx-side/2, cx+side/2); self.ax3.set_ylim(cy-side/2, cy+side/2)
        self.ax3.set_aspect('equal', adjustable='datalim'); self.ax3.set_box_aspect(1)
        self.ax3.set_xlabel('$x/c$'); self.ax3.set_ylabel('$y/c$',rotation=0)
        if self.ctrl.show_legend.isChecked():
            self.ax3.legend()

        blade_cx, blade_cy = 0.25, 0.0
        blade_half_x, blade_half_y = 0.75*self.ctrl.plot_scale, 1.0*self.ctrl.plot_scale
        self.ax.set_xlim(blade_cx-blade_half_x, blade_cx+blade_half_x)
        self.ax.set_ylim(blade_cy-blade_half_y, blade_cy+blade_half_y)

        if self.ctrl.show_grid.isChecked():
            self.ax.grid(alpha=.3); self.ax2.grid(alpha=.3); self.ax3.grid(alpha=.3)

        self.canvas.draw_idle()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save image", "blade.png", "Images (*.png *.pdf *.svg)")
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
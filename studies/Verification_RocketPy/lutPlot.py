import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt

# Data from your file
data = [
    [0, 0.2314, 0.2806, 0.3542, 0.4275],
    [0.3, 0.2314, 0.2806, 0.3542, 0.4275],
    [0.6, 0.2264, 0.2743, 0.3468, 0.4195],
    [0.8, 0.2311, 0.2782, 0.3509, 0.425],
    [0.85, 0.2926, 0.3396, 0.413, 0.4884],
    [0.9, 0.4015, 0.4485, 0.5235, 0.6015],
    [0.95, 0.5791, 0.6259, 0.7012, 0.7802],
    [1, 0.7467, 0.7926, 0.8655, 0.9413],
    [1.05, 0.8308, 0.8755, 0.9443, 1.0147],
    [1.1, 0.8357, 0.8791, 0.9433, 1],
    [1.15, 0.808, 0.8502, 0.9107, 0.9696],
    [1.2, 0.7782, 0.8197, 0.8783, 0.9347],
    [1.25, 0.7387, 0.7799, 0.8382, 0.8929],
    [1.3, 0.7208, 0.7615, 0.8191, 0.8742],
    [1.4, 0.723, 0.7616, 0.818, 0.87],
    [1.5, 0.7237, 0.7626, 0.8175, 0.8697],
    [1.8, 0.7237, 0.762, 0.817, 0.869],
    [2, 0.7237, 0.76, 0.816, 0.868],
]

data = np.array(data)
mach_numbers = data[:, 0]
ld_ratios = [10, 15, 22.5, 30]
drag_coeffs = data[:, 1:]

# Create grid for interpolation
mach_grid_dense = np.linspace(mach_numbers.min(), mach_numbers.max(), 200)
ld_grid_dense = np.linspace(ld_ratios[0], ld_ratios[-1], 200)
ld_mesh, mach_mesh = np.meshgrid(ld_grid_dense, mach_grid_dense)

# Prepare points and values for griddata
points = np.array([[m, ld] for m in mach_numbers for ld in ld_ratios])
values = drag_coeffs.flatten()

# Interpolate
drag_coeffs_interp = griddata(points, values, (mach_mesh, ld_mesh), method='cubic')
plt.rcParams.update({'font.size': 16})  # Set global font size to 20
plt.figure(figsize=(8, 6))
im = plt.imshow(
    drag_coeffs_interp,
    aspect='auto',
    interpolation='bilinear',
    cmap='coolwarm',
    extent=[ld_ratios[0], ld_ratios[-1], mach_numbers[-1], mach_numbers[0]],
    origin='upper'
)
plt.colorbar(im, label='$C_D$')

# Set contour levels starting at 0.4 in steps of 0.1
min_level = max(0.4, np.nanmin(drag_coeffs_interp))
max_level = np.nanmax(drag_coeffs_interp)
levels = np.arange(np.floor(min_level * 10) / 10, np.ceil(max_level * 10) / 10 + 0.1, 0.2)


levels = levels[levels >= 0.4]  # Ensure all levels are >= 0.4

contours = plt.contour(
    ld_mesh, mach_mesh, drag_coeffs_interp,
    levels=levels,
    colors='black', linewidths=1
)
plt.clabel(contours, inline=True, fontsize=16, fmt="%.1f")
plt.xlabel("$L/D$")
plt.ylabel("$Ma$")
#plt.title("$C_D$ over Mach number and $L/D$ ratio")

plt.tight_layout()
plt.savefig("drag_coefficient_heatmap.png", dpi=300)

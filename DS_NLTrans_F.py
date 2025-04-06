import streamlit as st
import math

def calculate_head_depth(head_type, R, aspect_ratio=2.0):
    """Calculate depth of different head types with proper geometry"""
    if "Hemispherical" in head_type:
        return R  # Depth = radius for hemispherical
    elif "Ellipsoidal" in head_type:
        # For 2:1 ellipsoidal heads (major axis/minor axis = 2:1)
        return R / aspect_ratio  # Typically R/2 for standard 2:1 heads
    return 0.0

def calculate_position(nozzle, support_height, R, L):
    """Calculate nozzle position in global coordinates with proper head geometry"""
    location = nozzle['location']
    θ = math.radians(nozzle['theta'])
    offset = nozzle['offset']
    
    # Horizontal components (X-Z plane)
    X = offset * math.sin(θ)
    Z = -offset * math.cos(θ)  # 0° = -Z direction
    
    # Vertical component (Y-axis) with proper head geometry
    if location == "Shell":
        Y = support_height + nozzle['elevation']
    else:
        head_type = "Hemispherical" if "Hemispherical" in location else "Ellipsoidal"
        aspect_ratio = nozzle.get('aspect_ratio', 2.0)
        head_depth = calculate_head_depth(head_type, R, aspect_ratio)
        
        if "Top" in location:
            # Top head position calculation
            base_elevation = support_height + L
            if "Hemispherical" in location:
                Y = base_elevation + head_depth - math.sqrt(head_depth**2 - offset**2)
            else:  # Ellipsoidal
                k = aspect_ratio
                Y = base_elevation + head_depth * (1 - math.sqrt(1 - (offset**2)/(R**2)))
        else:  # Bottom head
            base_elevation = support_height
            if "Hemispherical" in location:
                Y = base_elevation - head_depth + math.sqrt(head_depth**2 - offset**2)
            else:  # Ellipsoidal
                k = aspect_ratio
                Y = base_elevation - head_depth * (1 - math.sqrt(1 - (offset**2)/(R**2)))
    
    return X, Y, Z

def transform_loads(nozzle, support_height, R, L):
    """Transform local loads to global coordinate system"""
    X, Y, Z = calculate_position(nozzle, support_height, R, L)
    θ = math.radians(nozzle['theta'])
    
    if "Head" in nozzle['location']:
        # Head nozzle transformation
        Fy = nozzle['P']  # Axial load directly contributes to vertical
        Fx = nozzle['V1'] * math.sin(θ) + nozzle['V2'] * math.cos(θ)
        Fz = -nozzle['V1'] * math.cos(θ) + nozzle['V2'] * math.sin(θ)
    else:
        # Shell nozzle transformation
        Fx = nozzle['P'] * math.sin(θ) + nozzle['Vc'] * math.cos(θ)
        Fy = nozzle['VL']
        Fz = -nozzle['P'] * math.cos(θ) + nozzle['Vc'] * math.sin(θ)
    
    # Moment calculation
    Mx = Y * Fz - Z * Fy
    My = Z * Fx - X * Fz
    Mz = X * Fy - Y * Fx
    
    return Fx, Fy, Fz, Mx, My, Mz
 
def main():
    st.title("Vertical Vessel Nozzle Load Calculator")
    
    # Vessel parameters
    col1, col2, col3 = st.columns(3)
    support_height = col1.number_input("Support Height (m)", 0.0, 100.0, 0.0)
    R = col2.number_input("Vessel Radius (m)", 0.1, 10.0, 1.0)
    L = col3.number_input("Cylinder Length (m)", 0.0, 50.0, 10.0)
 
    # Nozzle inputs
    nozzles = []
    num_nozzles = st.number_input("Number of Nozzles", 1, 20, 1)
    
    for i in range(num_nozzles):
        st.markdown(f"### Nozzle {i+1}")
        cols = st.columns([2,1,1,1])
        
        # Location selection
        location = cols[0].selectbox(
            "Location", [
                "Shell", "Hemispherical Top Head",
                "Hemispherical Bottom Head",
                "Ellipsoidal Top Head", "Ellipsoidal Bottom Head"
            ], key=f"loc_{i}")
        
        # Position parameters
        if location == "Shell":
            elevation = cols[1].number_input("Elevation (m)", 0.0, L, 0.0, key=f"ele_{i}")
            theta = cols[2].number_input("Orientation (°)", -180.0, 180.0, 0.0, key=f"ang_{i}")
            offset = 0.0
            aspect_ratio = 2.0
        else:
            head_type = "Hemispherical" if "Hemispherical" in location else "Ellipsoidal"
            max_offset = calculate_head_depth(head_type, R)
            offset = cols[1].number_input("Offset (m)", 0.0, max_offset, 0.0, key=f"off_{i}")
            theta = cols[2].number_input("Orientation (°)", -180.0, 180.0, 0.0, key=f"ang_{i}")
            elevation = 0.0
            aspect_ratio = cols[3].number_input("Aspect Ratio", 1.5, 4.0, 2.0, key=f"ar_{i}") if "Ellipsoidal" in location else 2.0
        
        # Load inputs
        st.markdown("**Local Loads**")
        cols_load = st.columns(3)
        
        if "Head" in location:
            P = cols_load[0].number_input("P (Axial/Y) (N)", key=f"P_{i}")
            V1 = cols_load[1].number_input("V1 (Radial) (N)", key=f"V1_{i}")
            V2 = cols_load[2].number_input("V2 (Circ.) (N)", key=f"V2_{i}")
        else:
            P = cols_load[0].number_input("P (Axial) (N)", key=f"P_{i}")
            Vc = cols_load[1].number_input("Vc (Circ.) (N)", key=f"Vc_{i}")
            VL = cols_load[2].number_input("VL (Long.) (N)", key=f"VL_{i}")
        
        nozzles.append({
            "location": location,
            "offset": offset,
            "elevation": elevation,
            "theta": theta,
            "aspect_ratio": aspect_ratio,
            "P": P,
            "V1": V1 if "Head" in location else 0,
            "V2": V2 if "Head" in location else 0,
            "Vc": Vc if location == "Shell" else 0,
            "VL": VL if location == "Shell" else 0
        })
 
    if st.button("Calculate Foundation Loads"):
        total_Fx = total_Fy = total_Fz = 0.0
        total_Mx = total_My = total_Mz = 0.0
 
        for nozzle in nozzles:
            Fx, Fy, Fz, Mx, My, Mz = transform_loads(nozzle, support_height, R, L)
            total_Fx += Fx
            total_Fy += Fy
            total_Fz += Fz
            total_Mx += Mx
            total_My += My
            total_Mz += Mz
 
        st.success("### Final Foundation Loads")
        cols = st.columns(2)
        cols[0].metric("Σ Fx (N)", f"{total_Fx:.1f}")
        cols[1].metric("Σ Fy (N)", f"{total_Fy:.1f}")
        cols[0].metric("Σ Fz (N)", f"{total_Fz:.1f}")
        cols[1].metric("Σ Mx (Nm)", f"{total_Mx:.1f}")
        cols[0].metric("Σ My (Nm)", f"{total_My:.1f}")
        cols[1].metric("Σ Mz (Nm)", f"{total_Mz:.1f}")
 
if __name__ == "__main__":
    main()

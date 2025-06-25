import streamlit as st
import math
import pandas as pd
import os


def calculate_head_depth(head_type, R, aspect_ratio=2.0):
    """Calculate depth of different head types with proper geometry"""
    if "Hemispherical" in head_type:
        return R
    elif "Ellipsoidal" in head_type:
        return R / aspect_ratio
    return 0.0


def calculate_position(component, support_height, R, L):
    """Calculate component position in global coordinates with proper head geometry"""
    location = component['location']
    θ = math.radians(component['theta'])
    offset = component['offset']
    
    # Horizontal components (X-Z plane)
    X = offset * math.sin(θ)
    Z = -offset * math.cos(θ)
    
    # Vertical component (Y-axis)
    if location == "Shell":
        Y = support_height + component['elevation']
    else:
        head_type = "Hemispherical" if "Hemispherical" in location else "Ellipsoidal"
        aspect_ratio = component.get('aspect_ratio', 2.0)
        head_depth = calculate_head_depth(head_type, R, aspect_ratio)
        
        if "Top" in location:
            base_elevation = support_height + L
            if offset == 0:
                Y = base_elevation + head_depth
            else:
                if "Hemispherical" in location:
                    Y = base_elevation + math.sqrt(head_depth**2 - offset**2)
                else:
                    Y = base_elevation + head_depth * math.sqrt(1 - (offset**2)/(R**2))
        else:
            base_elevation = support_height
            if offset == 0:
                Y = base_elevation - head_depth
            else:
                if "Hemispherical" in location:
                    Y = base_elevation - math.sqrt(head_depth**2 - offset**2)
                else:
                    Y = base_elevation - head_depth * math.sqrt(1 - (offset**2)/(R**2))
    
    return X, Y, Z


def transform_nozzle_loads(nozzle, support_height, R, L):
    """Transform local nozzle loads to global coordinate system"""
    X, Y, Z = calculate_position(nozzle, support_height, R, L)
    θ = math.radians(nozzle['theta'])
    
    if "Head" in nozzle['location']:
        if "Top" in nozzle['location']:
            Fx = nozzle['V1'] * math.sin(θ) + nozzle['V2'] * math.cos(θ)
            Fy = nozzle['P']
            Fz = -nozzle['V1'] * math.cos(θ) + nozzle['V2'] * math.sin(θ)
        else:
            Fx = -nozzle['V1'] * math.sin(θ) + nozzle['V2'] * math.cos(θ)
            Fy = -nozzle['P']
            Fz = nozzle['V1'] * math.cos(θ) + nozzle['V2'] * math.sin(θ)
    else:
        Fx = nozzle['P'] * math.sin(θ) + nozzle['Vc'] * math.cos(θ)
        Fy = nozzle['VL']
        Fz = -nozzle['P'] * math.cos(θ) + nozzle['Vc'] * math.sin(θ)
    
    # Moment calculation (r × F)
    Mx = Y * Fz - Z * Fy
    My = Z * Fx - X * Fz
    Mz = X * Fy - Y * Fx
    
    return {
        'Fx': Fx,
        'Fy': Fy,
        'Fz': Fz,
        'Mx': Mx,
        'My': My,
        'Mz': Mz
    }


def transform_support_loads(support, support_height, R, L):
    """Transform pipe support loads to global coordinate system"""
    X, Y, Z = calculate_position(support, support_height, R, L)
    θ = math.radians(support['theta'])
    
    # Transform horizontal load components (Fh1 is radial, Fh2 is circumferential)
    Fx = support['Fh1'] * math.sin(θ) + support['Fh2'] * math.cos(θ)
    Fy = support['Fv']  # Vertical load is already in global Y direction
    Fz = -support['Fh1'] * math.cos(θ) + support['Fh2'] * math.sin(θ)
    
    # Moment calculation (r × F)
    Mx = Y * Fz - Z * Fy
    My = Z * Fx - X * Fz
    Mz = X * Fy - Y * Fx
    
    return {
        'Fx': Fx,
        'Fy': Fy,
        'Fz': Fz,
        'Mx': Mx,
        'My': My,
        'Mz': Mz
    }


def display_results(nozzle_results, support_results=None):
    """Display comprehensive results table with individual component loads and totals"""
    # Combine all results
    all_results = nozzle_results.copy()
    if support_results:
        all_results.extend(support_results)
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Calculate totals
    totals = {
        'Tag No.': 'TOTAL',
        'Type': '',
        'Fx': df['Fx'].sum(),
        'Fy': df['Fy'].sum(),
        'Fz': df['Fz'].sum(),
        'Mx': df['Mx'].sum(),
        'My': df['My'].sum(),
        'Mz': df['Mz'].sum()
    }
    
    # Format numbers
    formatted_df = df.copy()
    for col in ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']:
        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.2f}")
    
    # Build a one-row DataFrame for the totals
    totals_row = pd.DataFrame([{
        'Tag No.': 'TOTAL',
        'Type': '',
        'Fx':    f"{totals['Fx']:,.2f}",
        'Fy':    f"{totals['Fy']:,.2f}",
        'Fz':    f"{totals['Fz']:,.2f}",
        'Mx':    f"{totals['Mx']:,.2f}",
        'My':    f"{totals['My']:,.2f}",
        'Mz':    f"{totals['Mz']:,.2f}"
    }])


    # Concatenate the totals row onto the formatted DataFrame
    formatted_df = pd.concat([formatted_df, totals_row], ignore_index=True)


    # Display
    st.markdown("#### Loads Transformed to Foundation (Global Coordinates)")
    st.table(formatted_df)
    st.markdown("* All forces in Newtons (N) and moments in Newton-meters (Nm)*")   
    st.markdown("* 0 degree orientation aligned with -Z global direction*")       
    st.markdown("* +ve values : P otward on shell, upward on Top Head and downward on Btm Head.*")   
    st.markdown("* +ve values : VL Vert.upward on shell, V1 Horz.outward on Top Head and Inward on Btm Head.*")   
    st.markdown("* +ve values : Vc and V2 Horz.Tangential in direction of right hand thumb and will rotate with clockwise orientation.*")   
    st.markdown("* Image can be referred for alignment of local direction with Global direction as it transformrms to*")   
    st.markdown("* This is Beta version for test and feedback*")   

    st.markdown(
        "<h1 style='text-align: Right; color: cyan; font-size: 16px; font-family: Montserrat;'>Ag*</h1>",
        unsafe_allow_html=True
    )


def main():
    st.markdown(
        "<h1 style='text-align: Left; color: cyan; font-size: 24px; font-family: Montserrat;'>Vertical Vessel/Column Load Trans. at base-Local to Global</h1>",
        unsafe_allow_html=True
    )
    
    # Vessel parameters
    col1, col2, col3 = st.columns(3)
    support_height = col1.number_input("Support Height (m)", 0.0, 50.0, 1.0)
    R = col2.number_input("Vessel Radius (m)", 0.1, 10.0, 1.0)
    L = col3.number_input("Cylinder Length (m)", 0.0, 100.0, 10.0)
 
    # Tab interface for nozzles and supports
    tab1, tab2 = st.tabs(["Nozzles", "Pipe Supports"])
    
    with tab1:
        # Nozzle inputs
        nozzles = []
        num_nozzles = st.number_input("Number of Nozzles", 0, 20, 1, key="num_nozzles")
        
        for i in range(num_nozzles):
            # Create a container for each nozzle with image on left and inputs on right
            nozzle_container = st.container()
            
            with nozzle_container:
                cols = st.columns([1, 3])  # 1 part for image, 3 parts for inputs
                
                with cols[0]:  # Image column
                    # Location selection (we'll get this before showing the image)
                    location = cols[1].selectbox(
                        "Location", [
                            "Shell", "Hemispherical Top Head",
                            "Hemispherical Bottom Head",
                            "Ellipsoidal Top Head", "Ellipsoidal Bottom Head"
                        ], key=f"loc_{i}")
                    
                    # Display image based on location
                    image_map = {
                        "Shell": "images/shell.png",
                        "Hemispherical Top Head": "images/hemi_top.png",
                        "Hemispherical Bottom Head": "images/hemi_bottom.png",
                        "Ellipsoidal Top Head": "images/ellip_top.png",
                        "Ellipsoidal Bottom Head": "images/ellip_bottom.png"
                    }
                    
                    image_path = image_map.get(location)
                    if image_path and os.path.exists(image_path):
                        st.image(image_path,
                                caption=f"{location} Nozzle",
                                width=180)  # Adjust width as needed
                    else:
                        st.warning(f"Image not found: {image_path}")
                
                with cols[1]:  # Inputs column
                    st.markdown(f"### Nozzle {i+1}")
                    
                    # Tag number input
                    tag_no = st.text_input(f"Tag Number", key=f"nozzle_tag_{i}", value=f"N-{i+1}")
                    
                    # Position parameters
                    if location == "Shell":
                        elevation = st.number_input("Elevation (m)", 0.0, L, 0.0, key=f"ele_{i}")
                        theta = st.number_input("Orientation (°)", 0, 359, 0, key=f"ang_{i}")
                        offset = 0.0
                        aspect_ratio = 2.0
                    else:
                        head_type = "Hemispherical" if "Hemispherical" in location else "Ellipsoidal"
                        max_offset = calculate_head_depth(head_type, R)
                        offset = st.number_input("Offset (m)", 0.0, max_offset, 0.0, key=f"off_{i}")
                        theta = st.number_input("Orientation (°)", 0, 359, 0, key=f"ang_{i}")
                        elevation = 0.0
                        aspect_ratio = st.number_input("Aspect Ratio", 1.5, 4.0, 2.0, key=f"ar_{i}") if "Ellipsoidal" in location else 2.0
                    
                    # Load inputs
                    st.markdown("**Local Loads**")
                    cols_load = st.columns(3)
                    
                    if "Head" in location:
                        P = cols_load[0].number_input("P (Axial) (N)", key=f"P_{i}")
                        V1 = cols_load[1].number_input("V1 (Radial) (N)", key=f"V1_{i}")
                        V2 = cols_load[2].number_input("V2 (Circumferential) (N)", key=f"V2_{i}")
                        Vc = 0
                        VL = 0
                    else:
                        P = cols_load[0].number_input("P (Axial) (N)", key=f"P_{i}")
                        Vc = cols_load[1].number_input("Vc (Circumferential) (N)", key=f"Vc_{i}")
                        VL = cols_load[2].number_input("VL (Longitudinal) (N)", key=f"VL_{i}")
                        V1 = 0
                        V2 = 0
                    
                    # Store nozzle data
                    nozzles.append({
                        "location": location,
                        "offset": offset,
                        "elevation": elevation,
                        "theta": theta,
                        "aspect_ratio": aspect_ratio,
                        "P": P,
                        "V1": V1,
                        "V2": V2,
                        "Vc": Vc,
                        "VL": VL,
                        "tag_no": tag_no,
                        "type": "Nozzle"
                    })
    with tab2:
        # Pipe support inputs
        supports = []
        num_supports = st.number_input("Number of Pipe Supports", 0, 20, 0, key="num_supports")
        
        for i in range(num_supports):
            st.markdown(f"### Pipe Support {i+1}")
            
            # Tag number input
            tag_no = st.text_input(f"Tag Number", key=f"support_tag_{i}", value=f"PS-{i+1}")
            
            cols = st.columns([2,1,1])
            
            # Location selection (pipe supports are only on shell)
            location = "Shell"
            
            # Position parameters
            elevation = cols[0].number_input("Elevation (m)", 0.0, L, 0.0, key=f"sp_ele_{i}")
            theta = cols[1].number_input("Orientation (°)", 0, 359, 0, key=f"sp_ang_{i}")
            offset = cols[2].number_input("Offset (m)", 0.0, R+2, 0.0, key=f"sp_off_{i}")
            
            # Load inputs
            st.markdown("**Support Loads**")
            cols_load = st.columns(3)
            
            Fv = cols_load[0].number_input("Vertical Load (N)", key=f"Fv_{i}")
            Fh1 = cols_load[1].number_input("Radial Load (N)", key=f"Fh1_{i}")
            Fh2 = cols_load[2].number_input("Circumferential Load (N)", key=f"Fh2_{i}")
            
            # Store support data
            supports.append({
                "location": location,
                "offset": offset,
                "elevation": elevation,
                "theta": theta,
                "aspect_ratio": 2.0,  # Not used for supports
                "Fv": Fv,
                "Fh1": Fh1,
                "Fh2": Fh2,
                "tag_no": tag_no,
                "type": "Pipe Support"
            })


    if st.button("Calculate Foundation Loads"):
        nozzle_results = []
        support_results = []
        
        # Process nozzles
        for nozzle in nozzles:
            result = transform_nozzle_loads(nozzle, support_height, R, L)
            nozzle_results.append({
                'Tag No.': nozzle['tag_no'],
                'Type': nozzle['type'],
                'Fx': result['Fx'],
                'Fy': result['Fy'],
                'Fz': result['Fz'],
                'Mx': result['Mx'],
                'My': result['My'],
                'Mz': result['Mz']
            })
        
        # Process pipe supports
        for support in supports:
            result = transform_support_loads(support, support_height, R, L)
            support_results.append({
                'Tag No.': support['tag_no'],
                'Type': support['type'],
                'Fx': result['Fx'],
                'Fy': result['Fy'],
                'Fz': result['Fz'],
                'Mx': result['Mx'],
                'My': result['My'],
                'Mz': result['Mz']
            })
        
        # Display comprehensive results
        display_results(nozzle_results, support_results)


if __name__ == "__main__":
    main()
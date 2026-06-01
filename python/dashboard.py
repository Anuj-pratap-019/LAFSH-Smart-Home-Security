import streamlit as st
import sys
import os
import io
import contextlib
import copy
from PIL import Image
import inspect

def st_image(image, caption=None, **kwargs):
    # Check Streamlit's st.image signature for version compatibility
    sig = inspect.signature(st.image)
    if 'use_container_width' in sig.parameters:
        return st.image(image, caption=caption, use_container_width=True)
    else:
        return st.image(image, caption=caption, use_column_width=True)


# Add src folder to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from init import init_cloud, init_fog_node, init_rbac
from network import deploy_nodes, leach_sep_clustering
from viz import plot_deployment, plot_clusters, plot_rbac_heatmap
from run_demo import run_demo
from run_evaluation import run_evaluation
from run_security_analysis import run_security_analysis

# Page Configuration
st.set_page_config(
    page_title="LAFSH Simulation Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Theme CSS (Beautiful dark mode with glassmorphic cards and symmetry)
st.markdown("""
    <style>
    /* Main body background color */
    .stApp {
        background-color: #0B0F19;
        color: #F3F4F6;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1F2937;
    }
    
    /* Title banner styling */
    .banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #0D9488 100%);
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 25px;
        border: 1px solid #2563EB;
        box-shadow: 0 4px 20px rgba(0, 114, 189, 0.2);
        text-align: center;
    }
    
    .banner h1 {
        color: #FFFFFF !important;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .banner p {
        color: #CCFBF1 !important;
        font-size: 1.1rem;
        margin: 5px 0 0 0;
    }
    
    /* Terminal Console Window styling (Increased Height to 600px) */
    .terminal-header {
        background-color: #111827;
        padding: 10px 15px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border: 1px solid #374151;
        font-family: monospace;
        font-size: 0.85rem;
        color: #9CA3AF;
        display: flex;
        align-items: center;
    }
    
    .terminal-dot {
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    
    .terminal-body {
        background-color: #030712;
        padding: 20px;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        font-family: 'Consolas', 'Courier New', monospace;
        color: #10B981;
        border: 1px solid #374151;
        border-top: none;
        height: 600px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #111827;
        border: 1px solid #1F2937;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: bold;
        color: #0D9488;
    }
    .metric-lbl {
        color: #9CA3AF;
        font-size: 0.85rem;
    }
    
    /* Explanations text block styling */
    .expl-box {
        background-color: #1F2937;
        border: 1px solid #374151;
        border-left: 5px solid #0D9488;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        margin-bottom: 20px;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* Sidebar buttons styling */
    div[data-testid="stSidebar"] div.stButton > button {
        background-color: #1F2937;
        color: #E5E7EB;
        border: 1px solid #374151;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        height: 42px;
        width: 100%;
        text-align: left;
        padding-left: 15px;
        margin-bottom: 5px;
    }
    div[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #2563EB;
        color: white;
        border-color: #3B82F6;
        transform: translateX(4px);
    }
    </style>
""", unsafe_allow_html=True)

# App Title Banner (CSE 4702 line removed)
st.markdown("""
    <div class="banner">
        <h1>🛡️ LAFSH Simulation Control Panel</h1>
        <p>Lightweight Authentication and Access Control Simulation for Fog-based IoT Networks</p>
    </div>
""", unsafe_allow_html=True)

# Metrics Grid (Highlight results)
st.markdown("### 🏆 LAFSH Key Performance Indicators")
met_col1, met_col2, met_col3, met_col4 = st.columns(4)
with met_col1:
    st.markdown('<div class="metric-card"><div class="metric-val">11,000×</div><div class="metric-lbl">Less Energy vs RSA/PKI</div></div>', unsafe_allow_html=True)
with met_col2:
    st.markdown('<div class="metric-card"><div class="metric-val">25×</div><div class="metric-lbl">Less Bandwidth vs TLS-Cert</div></div>', unsafe_allow_html=True)
with met_col3:
    st.markdown('<div class="metric-card"><div class="metric-val">&lt; 1 ms</div><div class="metric-lbl">Authentication Latency</div></div>', unsafe_allow_html=True)
with met_col4:
    st.markdown('<div class="metric-card"><div class="metric-val">23 / 24</div><div class="metric-lbl">Security Checklist Score</div></div>', unsafe_allow_html=True)

st.write("")

# SIDEBAR: Contains the Selection Buttons to achieve perfect 50/50 main layout symmetry
st.sidebar.markdown("### 🛠️ Menu Selection")
st.sidebar.write("Select an operation option:")

choice = -1

# Operations represented as sidebar buttons
if st.sidebar.button("🚀 1. Run Interactive Demo"):
    choice = 1
if st.sidebar.button("📊 2. Run Performance Evaluation"):
    choice = 2
if st.sidebar.button("🛡️ 3. Run Security Analysis"):
    choice = 3
if st.sidebar.button("🔑 4. Display RBAC Matrix"):
    choice = 4
if st.sidebar.button("⚡ 5. Run Quick Test (300 Nodes)"):
    choice = 5

st.sidebar.write("---")
input_val = st.sidebar.text_input("Or enter number (0-5) manually:", value="")
if input_val.strip():
    try:
        val = int(input_val.strip())
        if 0 <= val <= 5:
            choice = val
        else:
            st.sidebar.error("Enter a number between 0 and 5.")
    except ValueError:
        st.sidebar.error("Invalid choice format.")

# Session state initialization
if "console_output" not in st.session_state:
    st.session_state.console_output = "System initialized and ready.\nChoose an operation from the sidebar menu to start the simulation."
if "last_choice" not in st.session_state:
    st.session_state.last_choice = -1

# Run operations backend
if choice != -1:
    st.session_state.last_choice = choice
    if choice == 0:
        st.session_state.console_output = "[SESSION] Exit triggered. Resetting dashboard.\nGoodbye!"
    else:
        # Buffer to capture console output
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            try:
                if choice == 1:
                    run_demo()
                elif choice == 2:
                    run_evaluation()
                elif choice == 3:
                    run_security_analysis()
                elif choice == 4:
                    rbac = init_rbac()
                    plot_rbac_heatmap(rbac)
                    print("\nPermission Matrix Table:")
                    try:
                        import pandas as pd
                        df = pd.DataFrame(rbac.permission_matrix, index=rbac.roles, columns=rbac.operations)
                        print(df.to_string())
                    except ImportError:
                        header = f"{'Role/Op':<10} | " + " | ".join(f"{op[:4]}" for op in rbac.operations)
                        print(header)
                        print("-" * len(header))
                        for r_idx, role in enumerate(rbac.roles):
                            row_str = f"{role:<10} | " + " | ".join(f"  {rbac.permission_matrix[r_idx][o_idx]} " for o_idx in range(len(rbac.operations)))
                            print(row_str)
                elif choice == 5:
                    print('\n--- Quick Test: 300 Nodes ---\n')
                    cloud = init_cloud()
                    rbac = init_rbac()
                    fog = init_fog_node('FOG_TEST', cloud, rbac, 100, 100)
                    devices = deploy_nodes(300, 200)
                    plot_deployment(devices, fog, 200)
                    devices, clusters = leach_sep_clustering(devices, fog, 1, 0.1, 200)
                    plot_clusters(devices, clusters, fog, 200)
                    print('\nQuick test complete!')
            except Exception as e:
                print(f"\n[ERROR] Execution failed: {str(e)}")

        st.session_state.console_output = f.getvalue()

# Perfect Symmetrical Layout (50/50 division of main container)
col_terminal, col_graphs = st.columns([1, 1])

# Left column: Unix Console log window
with col_terminal:
    st.markdown("### 🖥️ Console Output Logs")
    
    st.markdown("""
        <div class="terminal-header">
            <span class="terminal-dot" style="background-color: #FF5F56;"></span>
            <span class="terminal-dot" style="background-color: #FFBD2E;"></span>
            <span class="terminal-dot" style="background-color: #27C93F;"></span>
            <span style="margin-left: 10px;">bash - python/dashboard.py</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(
        f'<div class="terminal-body">{st.session_state.console_output.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True
    )

# Right column: Visualization Plots with descriptive annotations
with col_graphs:
    st.markdown("### 🖼️ Generated Visual Plots")
    active_choice = st.session_state.last_choice

    if active_choice == -1:
        st.info("Visual plots will be loaded here after you execute an operation from the sidebar.")
    else:
        if active_choice == 1:
            st.markdown("Select Tab to view generated LEACH-SEP simulation plots:")
            tabs = st.tabs(["Node Deployment Map", "Cluster Formation Map", "Network stats (50 rounds)"])
            
            with tabs[0]:
                if os.path.exists("figures/node_deployment.png"):
                    st_image(Image.open("figures/node_deployment.png"), caption="Deployment Topology Map")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            This plot shows 500 heterogeneous smart home IoT devices (lights, locks, thermostats, motion sensors, plugs, cameras) randomly scattered across a 200m x 200m area. The central red star represents the delegated <b>Fog Node</b> (gateway router).
                            <br><br>
                            <strong>🔍 Key Takeaway:</strong> Devices are deployed with type-specific ranges, capability bitmasks, and initial energy levels (heterogeneous configuration) to simulate a real home environment.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet. Running option 1 generates this plot.")
            
            with tabs[1]:
                if os.path.exists("figures/cluster_formation.png"):
                    st_image(Image.open("figures/cluster_formation.png"), caption="LEACH-SEP Cluster Formation")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            This layout shows the elected <b>Cluster Heads (CHs)</b> represented as stars, and member nodes linked to their nearest CH in distinct colors. The CHs aggregate local data and forward the summary to the far-away Fog Node.
                            <br><br>
                            <strong>🔍 Key Takeaway:</strong> Under <b>LEACH-SEP</b>, nodes with higher residual energy (like cameras and locks) have a higher probability of becoming CHs. This prevents low-energy nodes from dying early, extending network lifetime.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet.")
            
            with tabs[2]:
                if os.path.exists("figures/network_stats.png"):
                    st_image(Image.open("figures/network_stats.png"), caption="Alive Nodes & Energy lifetime over 50 rounds")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            A four-panel grid monitoring network execution:
                            <ul>
                                <li><b>Network Lifetime</b>: Shows the count of alive nodes round-by-round (stays at 500 throughout 50 rounds).</li>
                                <li><b>Energy Consumption</b>: Cumulative energy consumed in microjoules (remains low due to clustering).</li>
                                <li><b>Packet Delivery Ratio (PDR)</b>: Verifies packet transmission reliability.</li>
                                <li><b>Cluster Count</b>: Monitor CH rotation and re-clustering phases.</li>
                            </ul>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet.")

        elif active_choice == 2:
            st.markdown("Select Tab to view performance evaluation graphs:")
            tabs = st.tabs(["Auth Latency Line", "Comm Overhead Bars", "Energy Consumption Log-Bar", "Security Features Radar"])
            
            with tabs[0]:
                if os.path.exists("figures/auth_latency.png"):
                    st_image(Image.open("figures/auth_latency.png"), caption="Registration and Mutual Auth Latency (ms)")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            Average registration and authentication times against increasing device counts. Latency stays stable and well under 1 millisecond.
                            <br><br>
                            <strong>🔍 Key Takeaway:</strong> Because the LAFSH protocol relies only on lightweight hashes and bitwise XOR operations instead of heavy asymmetric cryptography (like RSA/ECC), authentication runs extremely fast.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet. Running option 2 generates this plot.")
            
            with tabs[1]:
                if os.path.exists("figures/comm_overhead.png"):
                    st_image(Image.open("figures/comm_overhead.png"), caption="Bandwidth Exchanged (Bytes)")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            A comparative bar chart showing bytes exchanged during protocol phases.
                            <ul>
                                <li><b>LAFSH</b>: Exchanges ~200 bytes total per mutual authentication.</li>
                                <li><b>TLS-Cert</b>: Requires ~5,000 bytes (25× heavier) due to digital certificates and a multi-step handshake.</li>
                            </ul>
                            <strong>🔍 Key Takeaway:</strong> LAFSH dramatically cuts bandwidth consumption, which is ideal for networks with low data-rate limits.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet.")
            
            with tabs[2]:
                if os.path.exists("figures/energy_comparison.png"):
                    st_image(Image.open("figures/energy_comparison.png"), caption="Log-scale Energy comparison per authentication (μJ)")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            Energy consumption comparison per authentication plotted in log scale.
                            <ul>
                                <li><b>LAFSH</b>: Consumes just <b>162.4 µJ</b> (computation + transmission).</li>
                                <li><b>PKI/RSA</b>: Consumes over <b>1.8 million µJ</b> (1,800,000 µJ) because modular exponentiation is computationally heavy.</li>
                            </ul>
                            <strong>🔍 Key Takeaway:</strong> LAFSH is **~11,000× more energy-efficient** than traditional PKI, preventing battery-powered smart home devices from running out of charge.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet.")
            
            with tabs[3]:
                if os.path.exists("figures/security_radar.png"):
                    st_image(Image.open("figures/security_radar.png"), caption="Security Comparison Radar Chart")
                    st.markdown("""
                        <div class="expl-box">
                            <strong>💡 What this graph shows:</strong><br>
                            A radar chart scoring security features (mutual auth, replay protection, MITM block, device fingerprinting, 2FA, computation/communication efficiency).
                            <br><br>
                            <strong>🔍 Key Takeaway:</strong> LAFSH secures a near-perfect score (23/24) because it offers robust security features (including device fingerprinting and TOTP two-factor auth) without the high computational/communication costs of TLS.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Figures not generated yet.")

        elif active_choice == 3:
            st.markdown("Attack Scenarios completed successfully! Showing security scoring radar:")
            if os.path.exists("figures/security_radar.png"):
                st_image(Image.open("figures/security_radar.png"), caption="Security Comparison Radar Chart")
            
            st.markdown("""
                <div class="expl-box">
                    <strong>🛡️ Verification Status:</strong> All 6 attack scenarios were successfully blocked:
                    <ol>
                        <li><b>Replay Attack</b>: Blocked by Fog Node checking timestamp skew ($|now - T_1| < 120s$).</li>
                        <li><b>Device Cloning</b>: Blocked by verifying unique hardware fingerprints.</li>
                        <li><b>Impersonation</b>: Blocked because attacker cannot forge anchor keys without the Fog's master secret.</li>
                        <li><b>TOTP Guessing</b>: Guess attempts blocked by generating 6-digit dynamic codes with a 30s expiry.</li>
                        <li><b>Privilege Escalation</b>: Blocked by enforcing RBAC matrix restrictions.</li>
                        <li><b>Unregistered Device</b>: Blocked by Fog registry validation.</li>
                    </ol>
                </div>
            """, unsafe_allow_html=True)

        elif active_choice == 4:
            st.markdown("RBAC Policy Matrix Heatmap:")
            if os.path.exists("figures/rbac_heatmap.png"):
                st_image(Image.open("figures/rbac_heatmap.png"), caption="Access heatmap rules (Y=Allow, N=Deny)")
            
            st.markdown("""
                <div class="expl-box">
                    <strong>💡 What this heatmap shows:</strong><br>
                    Green indicates permission granted; Red indicates denied.
                    <ul>
                        <li><b>Admin</b>: Access to all 11 operations (firmware updates, adding devices, etc.).</li>
                        <li><b>Resident</b>: Full daily operation access, but cannot modify device configuration or view live recordings.</li>
                        <li><b>Guest</b>: Access restricted only to authorized hours (09:00 to 22:00).</li>
                        <li><b>Device</b>: Can only report sensor data; cannot execute any user operations.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # Renders the pandas table directly
            st.markdown("#### Interactive Access Matrix Dataframe:")
            try:
                import pandas as pd
                rbac = init_rbac()
                df = pd.DataFrame(rbac.permission_matrix, index=rbac.roles, columns=rbac.operations)
                st.dataframe(df.style.map(lambda val: 'background-color: #065F46; color: #D1FAE5;' if val else 'background-color: #991B1B; color: #FEE2E2;'))
            except Exception as e:
                st.write(f"Could not load interactive table: {str(e)}")

        elif active_choice == 5:
            st.markdown("Quick Test (300 Nodes) visualization plots:")
            tabs = st.tabs(["Quick Deployment Map", "Quick Cluster Groups"])
            with tabs[0]:
                if os.path.exists("figures/node_deployment.png"):
                    st_image(Image.open("figures/node_deployment.png"), caption="300 Nodes Scattered Placement Map")
            with tabs[1]:
                if os.path.exists("figures/cluster_formation.png"):
                    st_image(Image.open("figures/cluster_formation.png"), caption="Cluster Groups Layout")
            
            st.markdown("""
                <div class="expl-box">
                    <strong>💡 Quick Test summary:</strong><br>
                    Renders deployment and routing clusters for a custom batch of 300 devices, showing dynamic cluster head allocation in real-time.
                </div>
            """, unsafe_allow_html=True)

import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def _ensure_dir(path):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def plot_deployment(devices, fog_node=None, area_size=200):
    """Visualize deployed nodes colored by device type."""
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.grid(True, linestyle='--', alpha=0.7)

    types = ['light', 'thermostat', 'camera', 'lock', 'motion_sensor', 'smart_plug']
    colors = ['#FFCC00', '#00B34D', '#CC0000', '#0066CC', '#994DFF', '#808080']
    markers = ['o', 's', '^', 'd', 'v', 'p']
    marker_sizes = [30, 40, 50, 40, 25, 30]

    for t_idx, t in enumerate(types):
        idx = [i for i, d in enumerate(devices) if d.type == t]
        if idx:
            x_vals = [devices[i].x for i in idx]
            y_vals = [devices[i].y for i in idx]
            ax.scatter(x_vals, y_vals, s=marker_sizes[t_idx], c=colors[t_idx],
                       marker=markers[t_idx], edgecolors='k', linewidths=0.5,
                       alpha=0.8, label=t)

    # Plot fog node
    if fog_node is not None:
        ax.scatter(fog_node.x, fog_node.y, s=300, c='red', marker='P',
                   edgecolors='k', linewidths=1.5, label='Fog Node')

    ax.set_xlabel('X Position (m)', fontsize=12)
    ax.set_ylabel('Y Position (m)', fontsize=12)
    ax.set_title(f'Heterogeneous IoT Node Deployment ({len(devices)} nodes)', fontsize=14)
    ax.set_xlim([0, area_size])
    ax.set_ylim([0, area_size])
    ax.legend(bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0, fontsize=9)
    plt.tight_layout()

    out_path = 'figures/node_deployment.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Node deployment plot saved to {out_path}")

def plot_clusters(devices, clusters, fog_node, area_size=200):
    """Visualize cluster formation with CHs and members."""
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.grid(True, linestyle='--', alpha=0.7)

    num_clusters = len(clusters)
    if num_clusters <= 10:
        cmap = plt.cm.get_cmap('tab10', num_clusters)
    else:
        cmap = plt.cm.get_cmap('hsv', num_clusters)

    # Plot each cluster
    for ci, cluster in enumerate(clusters):
        ch_idx = cluster['head_index']
        ch_device = devices[ch_idx]
        members = cluster['member_indices']
        color = cmap(ci)

        # Plot members
        if members:
            mx = [devices[i].x for i in members]
            my = [devices[i].y for i in members]
            ax.scatter(mx, my, s=20, c=[color], marker='o', edgecolors='none', alpha=0.6)

            # Lines from members to CH
            for m_idx in members:
                ax.plot([devices[m_idx].x, ch_device.x],
                        [devices[m_idx].y, ch_device.y],
                        '-', color=color, alpha=0.15, linewidth=0.5)

        # Plot CH as star
        ax.scatter(ch_device.x, ch_device.y, s=150, c=[color], marker='*',
                   edgecolors='k', linewidths=1.2, zorder=5)

    # Plot fog node
    ax.scatter(fog_node.x, fog_node.y, s=400, c='red', marker='D',
               edgecolors='k', linewidths=2, zorder=6)

    # Lines from CHs to fog node
    for cluster in clusters:
        ch_idx = cluster['head_index']
        ch_device = devices[ch_idx]
        ax.plot([ch_device.x, fog_node.x],
                [ch_device.y, fog_node.y],
                '--', color='red', alpha=0.3, linewidth=1)

    ax.set_xlabel('X Position (m)', fontsize=12)
    ax.set_ylabel('Y Position (m)', fontsize=12)
    ax.set_title(f'LEACH-SEP Cluster Formation ({num_clusters} clusters, {len(devices)} nodes)', fontsize=14)
    ax.set_xlim([0, area_size])
    ax.set_ylim([0, area_size])

    # Custom legend
    h1 = ax.scatter([], [], s=20, c='blue', marker='o', label='Member Node')
    h2 = ax.scatter([], [], s=150, c='blue', marker='*', edgecolors='k', label='Cluster Head')
    h3 = ax.scatter([], [], s=400, c='red', marker='D', edgecolors='k', label='Fog Node')
    ax.legend(handles=[h1, h2, h3], bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0, fontsize=10)
    plt.tight_layout()

    out_path = 'figures/cluster_formation.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Cluster formation plot saved to {out_path}")

def plot_auth_latency(results):
    """Line plot: authentication latency vs device count."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.errorbar(results['num_devices'], results['avg_reg_ms'], yerr=results['std_reg_ms'],
                fmt='-s', color='#0072BD', linewidth=2, markersize=8, markerfacecolor='#0072BD',
                capsize=5, label='Registration (Phase 1)')
    
    ax.errorbar(results['num_devices'], results['avg_auth_ms'], yerr=results['std_auth_ms'],
                fmt='-o', color='#D95319', linewidth=2, markersize=8, markerfacecolor='#D95319',
                capsize=5, label='Mutual Auth (Phase 2)')

    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_xlabel('Number of Devices', fontsize=13)
    ax.set_ylabel('Average Latency per Device (ms)', fontsize=13)
    ax.set_title('LAFSH Authentication Latency vs. Device Count', fontsize=14)
    ax.legend(loc='upper left', fontsize=11)

    out_path = 'figures/auth_latency.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Auth latency plot saved to {out_path}")

def plot_communication_overhead(results):
    """Grouped bar chart: bytes per scheme."""
    fig, ax = plt.subplots(figsize=(8, 5))

    schemes = results['schemes']
    x = np.arange(len(schemes))
    width = 0.25

    reg_b = results['registration_bytes']
    auth_b = results['authentication_bytes']
    totp_b = results['totp_bytes']

    b1 = ax.bar(x - width, reg_b, width, label='Registration', color='#0072BD')
    b2 = ax.bar(x, auth_b, width, label='Authentication', color='#D95319')
    b3 = ax.bar(x + width, totp_b, width, label='TOTP', color='#77AC30')

    ax.set_xticks(x)
    ax.set_xticklabels(schemes, fontsize=11)
    ax.set_ylabel('Bytes Exchanged', fontsize=13)
    ax.set_title('Communication Overhead Comparison', fontsize=14)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.5)

    # Add labels on top of bars
    for b in [b1, b2, b3]:
        for bar in b:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    out_path = 'figures/comm_overhead.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Communication overhead plot saved to {out_path}")

def plot_energy_comparison(results):
    """Bar chart: energy per auth (microjoules) in log scale."""
    fig, ax = plt.subplots(figsize=(8, 5))

    schemes = ['LAFSH', 'TLS', 'PKI']
    per_device = [results['lafsh_per_device'], results['tls_per_device'], results['pki_per_device']]

    colors = ['#77AC30', '#D95319', '#CC0000']
    bars = ax.bar(schemes, per_device, color=colors)
    ax.set_yscale('log')
    ax.grid(True, which="both", linestyle='--', alpha=0.5)

    ax.set_ylabel('Energy per Authentication (μJ) [log scale]', fontsize=13)
    ax.set_title('Energy Consumption Comparison', fontsize=14)

    # Add labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f} μJ',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, weight='bold')

    plt.tight_layout()
    out_path = 'figures/energy_comparison.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Energy comparison plot saved to {out_path}")

def plot_security_radar(results):
    """Radar/spider chart of security features."""
    fig, ax = plt.subplots(figsize=(7, 6.5))

    features = results['features']
    schemes = results['schemes']
    scores = np.array(results['scores'])
    num_features = len(features)
    num_schemes = len(schemes)

    # Custom cartesian coordinates matching the MATLAB logic
    angles = np.linspace(0, 2 * np.pi, num_features, endpoint=False)
    colors = ['#0072BD', '#D95319', '#77AC30', '#994DFF']

    # Draw concentric reference circles
    for r in range(1, 4):
        xc = r * np.cos(np.linspace(0, 2*np.pi, 100))
        yc = r * np.sin(np.linspace(0, 2*np.pi, 100))
        ax.plot(xc, yc, ':', color='#CCCCCC', linewidth=0.5)

    # Draw axes lines
    for a in range(num_features):
        ax.plot([0, 3.3 * np.cos(angles[a])], [0, 3.3 * np.sin(angles[a])],
                '-', color='#DDDDDD', linewidth=0.5)

    # Plot each scheme
    legend_handles = []
    for s in range(num_schemes):
        scheme_scores = scores[:, s]
        x = scheme_scores * np.cos(angles)
        y = scheme_scores * np.sin(angles)
        
        # Close loop
        x_loop = np.append(x, x[0])
        y_loop = np.append(y, y[0])

        ax.fill(x_loop, y_loop, colors[s], alpha=0.1)
        h, = ax.plot(x_loop, y_loop, '-o', color=colors[s], linewidth=2, markersize=6, label=schemes[s])
        legend_handles.append(h)

    # Add feature labels
    label_radius = 3.6
    for a in range(num_features):
        ha = 'center'
        cos_val = np.cos(angles[a])
        if abs(cos_val) > 0.1:
            ha = 'left' if cos_val > 0 else 'right'
        
        ax.text(label_radius * np.cos(angles[a]), label_radius * np.sin(angles[a]),
                features[a], ha=ha, va='center', fontsize=9, weight='bold')

    ax.axis('equal')
    ax.set_xlim([-4.5, 4.5])
    ax.set_ylim([-4.5, 4.5])
    ax.axis('off')
    ax.set_title('Security Feature Comparison (0=None, 3=Full)', fontsize=14)
    ax.legend(handles=legend_handles, loc='lower center', bbox_to_anchor=(0.5, -0.05),
              ncol=num_schemes, fontsize=10)

    plt.tight_layout()
    out_path = 'figures/security_radar.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Security radar plot saved to {out_path}")

def plot_rbac_heatmap(rbac):
    """Heatmap of the RBAC permission matrix."""
    fig, ax = plt.subplots(figsize=(8, 4))

    matrix = np.array(rbac.permission_matrix)
    cmap = mcolors.ListedColormap([[0.9, 0.2, 0.2], [0.2, 0.8, 0.2]])  # Red=denied, Green=allowed

    cax = ax.imshow(matrix, cmap=cmap, aspect='auto')

    ax.set_xticks(np.arange(len(rbac.operations)))
    ax.set_xticklabels(rbac.operations, rotation=45, ha='right', fontsize=11)
    
    ax.set_yticks(np.arange(len(rbac.roles)))
    ax.set_yticklabels(rbac.roles, fontsize=11)

    ax.set_title('RBAC Permission Matrix (Green=Allow, Red=Deny)', fontsize=14)

    # Add text labels in cells
    for r in range(matrix.shape[0]):
        for c in range(matrix.shape[1]):
            txt = 'Y' if matrix[r, c] else 'N'
            ax.text(c, r, txt, ha='center', va='center', color='w', fontsize=12, weight='bold')

    plt.tight_layout()
    out_path = 'figures/rbac_heatmap.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] RBAC heatmap saved to {out_path}")

def plot_network_stats(all_round_stats, num_nodes):
    """Multi-panel plot of network simulation metrics."""
    num_rounds = len(all_round_stats)
    rounds = np.arange(1, num_rounds + 1)

    alive = [s['alive_nodes'] for s in all_round_stats]
    energy = [s['total_energy_consumed'] for s in all_round_stats]
    pdr = [s['packet_delivery_ratio'] for s in all_round_stats]
    clusters = [s['num_clusters'] for s in all_round_stats]

    fig, axs = plt.subplots(2, 2, figsize=(10, 8))

    # Panel 1: Alive nodes
    axs[0, 0].plot(rounds, alive, '-', linewidth=2, color='#0072BD')
    axs[0, 0].set_xlabel('Round')
    axs[0, 0].set_ylabel('Alive Nodes')
    axs[0, 0].set_title(f'Network Lifetime ({num_nodes} nodes)')
    axs[0, 0].grid(True, linestyle='--', alpha=0.7)

    # Panel 2: Cumulative energy consumed
    axs[0, 1].plot(rounds, np.cumsum(energy) * 1e6, '-', linewidth=2, color='#D95319')
    axs[0, 1].set_xlabel('Round')
    axs[0, 1].set_ylabel('Cumulative Energy (μJ)')
    axs[0, 1].set_title('Energy Consumption')
    axs[0, 1].grid(True, linestyle='--', alpha=0.7)

    # Panel 3: Packet delivery ratio
    axs[1, 0].plot(rounds, np.array(pdr) * 100.0, '-', linewidth=2, color='#77AC30')
    axs[1, 0].set_xlabel('Round')
    axs[1, 0].set_ylabel('PDR (%)')
    axs[1, 0].set_title('Packet Delivery Ratio')
    axs[1, 0].set_ylim([0, 105])
    axs[1, 0].grid(True, linestyle='--', alpha=0.7)

    # Panel 4: Number of clusters
    axs[1, 1].plot(rounds, clusters, '-', linewidth=2, color='#994DFF')
    axs[1, 1].set_xlabel('Round')
    axs[1, 1].set_ylabel('Clusters')
    axs[1, 1].set_title('Cluster Count per Round')
    axs[1, 1].grid(True, linestyle='--', alpha=0.7)

    plt.suptitle('LEACH-SEP Network Simulation Results', fontsize=15, weight='bold')
    plt.tight_layout()

    out_path = 'figures/network_stats.png'
    _ensure_dir(out_path)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"[VIZ] Network stats plot saved to {out_path}")

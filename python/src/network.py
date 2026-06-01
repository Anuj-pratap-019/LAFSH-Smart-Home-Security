import random
import math
from utils import get_timestamp, sha256_hash, generate_nonce

class Device:
    def __init__(self):
        self.id = ""
        self.type = ""
        self.type_index = 0
        self.x = 0.0
        self.y = 0.0
        self.initial_energy = 0.0
        self.residual_energy = 0.0
        self.comm_range = 0.0
        self.data_rate = 0
        self.capability_mask = 0
        self.mac_address = ""
        self.firmware_version = ""
        self.reg_timestamp = 0
        self.fingerprint = ""
        self.role = "Device"
        self.registered = False
        self.authenticated = False
        self.session_key = ""
        self.password = ""
        self.totp_secret = ""
        self.credentials = {}
        self.cluster_id = -1
        self.is_cluster_head = False
        self.node_class = 0  # 1 = advanced, 0 = normal for SEP

def deploy_nodes(num_nodes, area_size=200):
    """Deploy heterogeneous IoT nodes in a smart home/neighborhood."""
    types = ['light', 'thermostat', 'camera', 'lock', 'motion_sensor', 'smart_plug']
    ratios = [0.30, 0.20, 0.15, 0.15, 0.10, 0.10]

    # Energy levels (Joules) per device type [initial_min, initial_max]
    energy_ranges = [
        [0.3, 0.5],   # light: low
        [0.5, 1.0],   # thermostat: medium
        [1.0, 2.0],   # camera: high
        [0.5, 1.0],   # lock: medium
        [0.2, 0.4],   # motion_sensor: very low
        [0.3, 0.5]    # smart_plug: low
    ]

    # Communication range (meters) per type
    comm_ranges = [15.0, 25.0, 30.0, 20.0, 10.0, 15.0]

    # Data rate (bytes/sec) per type
    data_rates = [10, 50, 500, 20, 5, 10]

    # Capability bitmask per type
    cap_masks = [
        0b00001,   # light: on/off
        0b00111,   # thermostat: on/off + read + write
        0b01011,   # camera: on/off + read + stream
        0b10101,   # lock: on/off + write + critical
        0b00010,   # motion_sensor: read only
        0b00001    # smart_plug: on/off
    ]

    # Firmware versions per type
    fw_versions = ['1.2.0', '2.1.3', '3.0.1', '2.5.0', '1.0.4', '1.1.2']

    # --- Assign types to nodes ---
    counts = [int(round(r * num_nodes)) for r in ratios]
    # Adjust for rounding issues
    counts[-1] = num_nodes - sum(counts[:-1])

    type_indices = []
    for t_idx, count in enumerate(counts):
        type_indices.extend([t_idx] * count)
    
    # Shuffle indices
    random.shuffle(type_indices)

    devices = []
    for i in range(num_nodes):
        ti = type_indices[i]
        d = Device()
        d.id = f"{types[ti].upper()}_{i + 1:04d}"
        d.type = types[ti]
        d.type_index = ti + 1  # 1-based indexing to match MATLAB output types if checked

        # Position
        d.x = random.random() * area_size
        d.y = random.random() * area_size

        # Energy
        e_min, e_max = energy_ranges[ti]
        d.initial_energy = e_min + random.random() * (e_max - e_min)
        d.residual_energy = d.initial_energy

        # Comm range (+/- 2.5m variation)
        d.comm_range = comm_ranges[ti] + (random.random() - 0.5) * 5.0

        # Data rate
        d.data_rate = data_rates[ti]

        # Capability
        d.capability_mask = cap_masks[ti]

        # Simulated MAC
        mac_bytes = [random.randint(0, 255) for _ in range(6)]
        d.mac_address = ":".join(f"{b:02X}" for b in mac_bytes)

        # Firmware
        d.firmware_version = fw_versions[ti]

        # Reg timestamp
        d.reg_timestamp = get_timestamp() + i

        # Fingerprint
        fp_input = f"{d.type}||{d.mac_address}||{d.firmware_version}||{d.capability_mask}||{d.reg_timestamp}"
        d.fingerprint = sha256_hash(fp_input)

        # Registration details
        d.registered = False
        d.authenticated = False
        d.session_key = ""
        d.password = generate_nonce(64)
        d.totp_secret = ""
        d.credentials = {}

        devices.append(d)

    print(f"[DEPLOY] {num_nodes} heterogeneous nodes deployed in {area_size}x{area_size} area")
    dist_str = " ".join(f"{types[t]}={counts[t]}" for t in range(len(types)))
    print(f"         Distribution: {dist_str}")
    return devices

def communicate(sender, receiver, data_bytes, distance=None):
    """Model energy cost of communication between two nodes using first-order radio model."""
    if distance is None:
        distance = math.sqrt((sender.x - receiver.x) ** 2 + (sender.y - receiver.y) ** 2)

    # Radio energy parameters
    E_elec = 50e-9       # 50 nJ/bit
    E_fs   = 10e-12      # 10 pJ/bit/m^2 (free space)
    E_mp   = 0.0013e-12  # 0.0013 pJ/bit/m^4 (multipath)
    d0     = math.sqrt(E_fs / E_mp)  # ~87.7m crossover

    k = data_bytes * 8  # bits

    # Transmission cost
    if distance < d0:
        E_tx = E_elec * k + E_fs * k * (distance ** 2)
    else:
        E_tx = E_elec * k + E_mp * k * (distance ** 4)

    # Reception cost
    E_rx = E_elec * k

    # Check energy levels
    if sender.residual_energy < E_tx or receiver.residual_energy < E_rx:
        return [E_tx, E_rx], False

    # Check communication range
    if distance > sender.comm_range * 3.0:
        return [E_tx, E_rx], False

    return [E_tx, E_rx], True

def leach_sep_clustering(devices, fog_node, round_num, p_opt=0.1, area_size=200):
    """LEACH-SEP clustering for heterogeneous IoT nodes."""
    N = len(devices)

    # Calculate average energy
    alive_nodes = [d for d in devices if d.residual_energy > 0]
    if not alive_nodes:
        return devices, []

    avg_energy = sum(d.residual_energy for d in devices) / N

    # Classify nodes (advanced vs normal)
    for d in devices:
        if d.residual_energy > avg_energy:
            d.node_class = 1  # advanced
        else:
            d.node_class = 0  # normal

    adv_nodes = [d for d in devices if d.node_class == 1]
    num_adv = len(adv_nodes)
    num_nrm = N - num_adv

    # Compute alpha (energy ratio)
    mean_adv = sum(d.residual_energy for d in adv_nodes) / max(num_adv, 1)
    nrm_nodes = [d for d in devices if d.node_class == 0]
    mean_nrm = sum(d.residual_energy for d in nrm_nodes) / max(num_nrm, 1)

    if mean_nrm > 0:
        alpha = (mean_adv / mean_nrm) - 1
    else:
        alpha = 0.5
    
    if math.isnan(alpha) or math.isinf(alpha):
        alpha = 0.5

    # SEP weighted probabilities
    p_nrm = p_opt / (1 + (num_adv / N) * alpha)
    p_adv = p_nrm * (1 + alpha)

    # Setup Phase
    for d in devices:
        d.cluster_id = -1
        d.is_cluster_head = False

    cluster_heads = []
    for idx, d in enumerate(devices):
        if d.residual_energy <= 0:
            continue

        p_i = p_adv if d.node_class == 1 else p_nrm

        # LEACH threshold formula: T(n) = p / (1 - p * mod(r, 1/p))
        denominator_mod = round(1 / p_i)
        r_mod = round_num % max(denominator_mod, 1)
        
        denom = 1 - p_i * r_mod
        if denom <= 0:
            threshold = 1.0
        else:
            threshold = p_i / denom

        # Energy-aware weighting
        energy_weight = d.residual_energy / d.initial_energy
        threshold *= energy_weight

        # Election check
        if random.random() < threshold:
            d.is_cluster_head = True
            cluster_heads.append(idx)

    # Fallback to ensure at least some CHs exist
    if not cluster_heads:
        sorted_indices = sorted(range(N), key=lambda i: devices[i].residual_energy, reverse=True)
        num_fallback = max(3, int(round(p_opt * N)))
        cluster_heads = [idx for idx in sorted_indices[:num_fallback] if devices[idx].residual_energy > 0]
        for idx in cluster_heads:
            devices[idx].is_cluster_head = True

    num_ch = len(cluster_heads)
    for ci, idx in enumerate(cluster_heads):
        devices[idx].cluster_id = ci + 1  # 1-based cluster indexing

    # Steady State Phase: Join nearest CH
    ch_coords = [(devices[idx].x, devices[idx].y) for idx in cluster_heads]
    for idx, d in enumerate(devices):
        if d.is_cluster_head or d.residual_energy <= 0:
            continue

        # Find nearest CH
        min_dist = float('inf')
        nearest_ci = -1
        for ci, (cx, cy) in enumerate(ch_coords):
            dist = math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest_ci = ci + 1
        d.cluster_id = nearest_ci

    # Build cluster summary objects
    clusters = []
    for ci, ch_idx in enumerate(cluster_heads):
        member_indices = [i for i, d in enumerate(devices) if d.cluster_id == ci + 1 and not d.is_cluster_head]
        
        ch_device = devices[ch_idx]
        
        # Distance to fog
        dist_to_fog = math.sqrt((ch_device.x - fog_node.x) ** 2 + (ch_device.y - fog_node.y) ** 2)

        # Type distribution
        type_distribution = {}
        if member_indices:
            for mi in member_indices:
                t = devices[mi].type
                type_distribution[t] = type_distribution.get(t, 0) + 1

        cluster = {
            'id': ci + 1,
            'head_index': ch_idx,
            'head_id': ch_device.id,
            'head_type': ch_device.type,
            'head_x': ch_device.x,
            'head_y': ch_device.y,
            'member_indices': member_indices,
            'num_members': len(member_indices),
            'dist_to_fog': dist_to_fog,
            'type_distribution': type_distribution
        }
        clusters.append(cluster)

    print(f"[CLUSTER] Round {round_num}: {num_ch} cluster heads elected out of {N} nodes")
    print(f"          Advanced nodes: {num_adv} | Normal nodes: {num_nrm}")
    avg_size = sum(c['num_members'] for c in clusters) / max(num_ch, 1)
    print(f"          Avg cluster size: {avg_size:.1f} members")
    return devices, clusters

def simulate_communication_round(devices, clusters, fog_node, round_num, data_bytes=128):
    """Simulate one round of cluster-based communication."""
    E_DA = 5e-9  # 5 nJ/bit/signal data fusion cost

    total_tx_energy = 0.0
    total_rx_energy = 0.0
    total_da_energy = 0.0
    total_packets = 0
    failed_packets = 0
    dead_nodes_before = sum(1 for d in devices if d.residual_energy <= 0)

    for cluster in clusters:
        ch_idx = cluster['head_index']
        ch_device = devices[ch_idx]

        # Skip if CH died
        if ch_device.residual_energy <= 0:
            continue

        members = cluster['member_indices']
        received_count = 0

        # Step 1: Members transmit to CH
        for m_idx in members:
            m_device = devices[m_idx]
            if m_device.residual_energy <= 0:
                continue

            e_cost, success = communicate(m_device, ch_device, data_bytes)
            total_packets += 1

            if success:
                # Deduct energy
                m_device.residual_energy -= e_cost[0]
                ch_device.residual_energy -= e_cost[1]
                
                total_tx_energy += e_cost[0]
                total_rx_energy += e_cost[1]
                received_count += 1
            else:
                failed_packets += 1

        # Step 2: CH data fusion
        if received_count > 0:
            da_energy = E_DA * data_bytes * 8 * received_count
            ch_device.residual_energy -= da_energy
            total_da_energy += da_energy

        # Step 3: CH sends aggregated data to Fog Node
        agg_bytes = data_bytes * 2
        dist_to_fog = cluster['dist_to_fog']
        e_cost, success = communicate(ch_device, fog_node, agg_bytes, dist_to_fog)
        total_packets += 1

        if success:
            ch_device.residual_energy -= e_cost[0]
            total_tx_energy += e_cost[0]
        else:
            failed_packets += 1

    dead_nodes_after = sum(1 for d in devices if d.residual_energy <= 0)
    alive_nodes = [d for d in devices if d.residual_energy > 0]
    avg_residual = sum(d.residual_energy for d in alive_nodes) / max(len(alive_nodes), 1)

    round_stats = {
        'round': round_num,
        'alive_nodes': len(alive_nodes),
        'dead_nodes': dead_nodes_after,
        'new_dead': dead_nodes_after - dead_nodes_before,
        'total_energy_consumed': total_tx_energy + total_rx_energy + total_da_energy,
        'avg_residual_energy': avg_residual if alive_nodes else 0.0,
        'total_packets': total_packets,
        'failed_packets': failed_packets,
        'packet_delivery_ratio': (total_packets - failed_packets) / max(total_packets, 1),
        'num_clusters': len(clusters)
    }

    return devices, round_stats

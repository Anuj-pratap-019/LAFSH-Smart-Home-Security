from utils import get_timestamp

def check_permission(device_id, operation, fog, sim_time=None):
    """RBAC policy enforcement at the fog layer."""
    if sim_time is None:
        sim_time = get_timestamp()

    rbac = fog.rbac

    # 1. Session check
    if device_id not in fog.active_sessions:
        permitted = False
        reason = 'No active session'
        fog = log_access(fog, device_id, 'Unknown', operation, permitted, reason, sim_time)
        return permitted, reason, fog

    session = fog.active_sessions[device_id]

    if sim_time > session['expires_at']:
        permitted = False
        reason = 'Session expired'
        del fog.active_sessions[device_id]
        fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
        return permitted, reason, fog

    # 2. TOTP check for user roles
    if session['role'] in ('Admin', 'Resident') and not session['totp_verified']:
        permitted = False
        reason = '2FA not completed - TOTP verification required'
        fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
        return permitted, reason, fog

    # 3. RBAC matrix check
    if session['role'] not in rbac.role_index:
        permitted = False
        reason = f"Unknown role: {session['role']}"
        fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
        return permitted, reason, fog

    if operation not in rbac.op_index:
        permitted = False
        reason = f"Unknown operation: {operation}"
        fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
        return permitted, reason, fog

    role_idx = rbac.role_index[session['role']]
    op_idx = rbac.op_index[operation]

    if rbac.permission_matrix[role_idx][op_idx] == 0:
        permitted = False
        reason = f'Role "{session["role"]}" denied operation "{operation}"'
        fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
        return permitted, reason, fog

    # 4. Guest time-window restriction
    if session['role'] == 'Guest':
        current_hour = int((sim_time // 3600) % 24)
        if current_hour < rbac.guest_window['start_hour'] or current_hour >= rbac.guest_window['end_hour']:
            permitted = False
            reason = f"Guest access denied outside hours {rbac.guest_window['start_hour']}:00-{rbac.guest_window['end_hour']}:00"
            fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
            return permitted, reason, fog

    # 5. PERMITTED
    permitted = True
    reason = f"ALLOWED: {session['role']} -> {operation}"
    fog = log_access(fog, device_id, session['role'], operation, permitted, reason, sim_time)
    return permitted, reason, fog

def log_access(fog, device_id, role, operation, permitted, reason, timestamp):
    status = 'PERMIT' if permitted else 'DENY'
    fog.audit_log.append({
        'timestamp': timestamp,
        'event': 'ACCESS_CHECK',
        'device_id': device_id,
        'role': role,
        'operation': operation,
        'status': status,
        'reason': reason
    })
    print(f"[RBAC] {status}: {device_id} ({role}) -> {operation} | {reason}")
    return fog

def display_audit_log(fog, filter_device=''):
    """Pretty-print the fog node's audit log."""
    log = fog.audit_log
    if not log:
        print("Audit log is empty.")
        return

    print("\n==================== AUDIT LOG ====================")
    print(f"{'TIMESTAMP':<12} {'EVENT':<16} {'DEVICE':<14} {'ROLE/OP':<12} {'STATUS':<8} {'DETAIL'}")
    print("-" * 80)

    for entry in log:
        if filter_device and entry['device_id'] != filter_device:
            continue

        ts_str = str(entry['timestamp'])
        
        role_op = ''
        if 'role' in entry and entry['role'] != 'Unknown':
            role_op = entry['role']
        if 'operation' in entry:
            role_op = entry['operation']

        detail = entry.get('reason', '')

        print(f"{ts_str:<12} {entry['event']:<16} {entry['device_id']:<14} {role_op:<12} {entry['status']:<8} {detail}")
    
    print("===================================================")
    print(f"Total entries: {len(log)}\n")

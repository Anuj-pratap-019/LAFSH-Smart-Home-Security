import sys
import os
import json

# Add src folder to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from init import init_rbac
from eval import (
    eval_auth_latency,
    eval_communication_overhead,
    eval_energy_estimation,
    eval_security_comparison
)
from viz import (
    plot_auth_latency,
    plot_communication_overhead,
    plot_energy_comparison,
    plot_security_radar,
    plot_rbac_heatmap
)

def run_evaluation():
    print('================================================================')
    print('  LAFSH Performance Evaluation Suite')
    print('================================================================\n')

    # Create output directories
    os.makedirs('results', exist_ok=True)
    os.makedirs('figures', exist_ok=True)

    # 1. Authentication Latency
    print('\n[1/5] Authentication Latency Evaluation...')
    latency_results = eval_auth_latency([50, 100, 200, 300, 500], 3)
    plot_auth_latency(latency_results)
    with open(os.path.join('results', 'eval_latency_results.json'), 'w') as f:
        json.dump(latency_results, f, indent=4)

    # 2. Communication Overhead
    print('\n[2/5] Communication Overhead Evaluation...')
    overhead_results = eval_communication_overhead()
    plot_communication_overhead(overhead_results)
    with open(os.path.join('results', 'eval_overhead_results.json'), 'w') as f:
        json.dump(overhead_results, f, indent=4)

    # 3. Energy Consumption
    print('\n[3/5] Energy Consumption Evaluation...')
    energy_results = eval_energy_estimation([50, 100, 200, 300, 500])
    plot_energy_comparison(energy_results)
    with open(os.path.join('results', 'eval_energy_results.json'), 'w') as f:
        json.dump(energy_results, f, indent=4)

    # 4. Security Comparison
    print('\n[4/5] Security Feature Comparison...')
    security_results = eval_security_comparison()
    plot_security_radar(security_results)
    with open(os.path.join('results', 'eval_security_results.json'), 'w') as f:
        json.dump(security_results, f, indent=4)

    # 5. RBAC Heatmap
    print('\n[5/5] RBAC Visualization...')
    rbac = init_rbac()
    plot_rbac_heatmap(rbac)

    print('\n================================================================')
    print('  EVALUATION COMPLETE')
    print('  Results saved to: results/')
    print('  Figures saved to: figures/')
    print('================================================================')
    print('\nGenerated plots:')
    print('  - figures/auth_latency.png')
    print('  - figures/comm_overhead.png')
    print('  - figures/energy_comparison.png')
    print('  - figures/security_radar.png')
    print('  - figures/rbac_heatmap.png')

if __name__ == '__main__':
    run_evaluation()

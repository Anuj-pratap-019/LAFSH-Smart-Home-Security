import sys
import os

# Add src folder to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from init import init_cloud, init_fog_node, init_rbac
from network import deploy_nodes, leach_sep_clustering
from viz import plot_deployment, plot_clusters, plot_rbac_heatmap
from run_demo import run_demo
from run_evaluation import run_evaluation
from run_security_analysis import run_security_analysis

def main():
    # Create directories
    os.makedirs('results', exist_ok=True)
    os.makedirs('figures', exist_ok=True)

    while True:
        print('================================================================')
        print('  LAFSH: Lightweight Authentication for Fog-based Smart Homes')
        print('  Fog Computing Course Project (CSE4702)')
        print('================================================================\n')

        print('Select an option:\n')
        print('  1. Run Interactive Demo (deployment + clustering + auth + RBAC)')
        print('  2. Run Performance Evaluation (latency, overhead, energy plots)')
        print('  3. Run Security Analysis (6 attack scenarios)')
        print('  4. Display RBAC Permission Matrix')
        print('  5. Quick Test (deploy 300 nodes + cluster + visualize)')
        print('  0. Exit\n')

        try:
            choice_str = input('Enter choice [1-5, 0 to exit]: ').strip()
            if not choice_str:
                continue
            choice = int(choice_str)
        except ValueError:
            print('Invalid input. Please enter a number.')
            continue

        if choice == 1:
            run_demo()
        elif choice == 2:
            run_evaluation()
        elif choice == 3:
            run_security_analysis()
        elif choice == 4:
            rbac = init_rbac()
            plot_rbac_heatmap(rbac)
            print('\nPermission Matrix:')
            try:
                import pandas as pd
                df = pd.DataFrame(rbac.permission_matrix, index=rbac.roles, columns=rbac.operations)
                print(df.to_string())
            except ImportError:
                # Fallback print if pandas isn't found
                header = f"{'Role/Op':<10} | " + " | ".join(f"{op[:4]}" for op in rbac.operations)
                print(header)
                print("-" * len(header))
                for r_idx, role in enumerate(rbac.roles):
                    row_str = f"{role:<10} | " + " | ".join(f"  {rbac.permission_matrix[r_idx][o_idx]} " for o_idx in range(len(rbac.operations)))
                    print(row_str)
            print()
        elif choice == 5:
            print('\n--- Quick Test: 300 Nodes ---\n')
            cloud = init_cloud()
            rbac = init_rbac()
            fog = init_fog_node('FOG_TEST', cloud, rbac, 100, 100)
            devices = deploy_nodes(300, 200)
            plot_deployment(devices, fog, 200)
            devices, clusters = leach_sep_clustering(devices, fog, 1, 0.1, 200)
            plot_clusters(devices, clusters, fog, 200)
            print('\nQuick test complete! Check the generated figures: figures/node_deployment.png and figures/cluster_formation.png\n')
        elif choice == 0:
            print('Goodbye!')
            break
        else:
            print('Invalid choice. Please choose between 0 and 5.')
        
        input('\nPress Enter to return to the main menu...')
        print('\n' * 2)

if __name__ == '__main__':
    main()

import os
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from config import config
from infrastructure.elasticsearch_integration import ElasticsearchManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visualize")

def fetch_data():
    """Fetch proposal data from Elasticsearch"""
    es_config = config.get_elasticsearch_config()
    try:
        es_manager = ElasticsearchManager(es_config)
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        return []
    
    index_name = f"{config.ELASTICSEARCH_INDEX_PREFIX}-reports"
    
    # Query to get all proposer logs
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"metadata.is_proposal": True}}
                ]
            }
        }
    }
    
    try:
        logger.info(f"Searching index {index_name} for proposal logs...")
        result = es_manager.es_client.search_logs(index_name, query, size=1000)
        
        data = []
        for hit in result.hits:
            service = hit.get("service", "")
            if service.startswith("aiops-proposer_"):
                proposer = service.replace("aiops-", "")
                incident_id = hit.get("incident_id", "unknown")
                metadata = hit.get("metadata", {})
                confidence_score = metadata.get("confidence_score", 0.0)
                model_name = metadata.get("model_name")
                
                # Fallback for older logs without model_name in metadata
                if not model_name:
                    try:
                        idx = int(proposer.split("_")[1])
                        model_name = config.PROPOSER_MODELS[idx].name
                    except (IndexError, ValueError, AttributeError):
                        pass
                        
                display_name = f"{proposer} ({model_name})" if model_name else proposer
                
                data.append({
                    "proposer": display_name,
                    "scenario": incident_id,
                    "confidence_score": confidence_score
                })
        
        logger.info(f"Fetched {len(data)} proposal records.")
        return data
        
    except Exception as e:
        logger.error(f"Error querying Elasticsearch: {e}")
        return []

def plot_efficiency_chart(data, output_file="docs/proposer_efficiency_chart.png"):
    """Plot grouped bar chart of confidence scores"""
    if not data:
        logger.warning("No data to plot.")
        return
    
    df = pd.DataFrame(data)
    
    # Sort data for consistent plotting
    df = df.sort_values(by=["scenario", "proposer"])
    
    # Setup plot
    plt.figure(figsize=(14, 8))
    sns.set_theme(style="whitegrid")
    
    # Create grouped bar chart
    ax = sns.barplot(
        data=df, 
        x="scenario", 
        y="confidence_score", 
        hue="proposer",
        palette="viridis"
    )
    
    # Customize the plot
    plt.title("Efficiency of Proposers across Scenarios (Confidence Score)", fontsize=16, pad=20)
    plt.xlabel("Scenarios", fontsize=12, labelpad=10)
    plt.ylabel("Confidence Score (0.0 - 1.0)", fontsize=12, labelpad=10)
    plt.ylim(0, 1.05)
    plt.legend(title="Proposer", title_fontsize='13', fontsize='11', loc='upper right', bbox_to_anchor=(1.15, 1))
    
    # Add value labels on top of bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.2f', padding=3, fontsize=9)
    
    plt.tight_layout()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the plot
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Chart successfully saved to {output_file}")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Proposer Efficiency from Elasticsearch")
    parser.add_argument("--output", type=str, default="docs/proposer_efficiency_chart.png", 
                        help="Path to save the generated chart")
    args = parser.parse_args()
    
    data = fetch_data()
    plot_efficiency_chart(data, args.output)

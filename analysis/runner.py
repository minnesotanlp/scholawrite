import data
import plotting
from taxonomy import Taxonomy

project_ids = [
  "6500d748909490ecba83e811",
  #"6578ec8845504beacf9d3dc7",
  "654682f220e7d557c7e67cff",
  "656a440644dec9f71f2dee44",
  "640e22cae918523bcee8ca5e",
  "656fadd102ae94a7686aae62"
]

#project_id = "6500d748909490ecba83e811"
#project_id = "640e22cae918523bcee8ca5e"

all_classes = Taxonomy["Planning"]["Classes"] + Taxonomy["Implementation"]["Classes"] + Taxonomy["Revision"]["Classes"]

color_map = data.color_node_map(all_classes)
color_map = {
  "Planning": Taxonomy["Planning"]["Color"],
  "Implementation": Taxonomy["Implementation"]["Color"],
  "Revision": Taxonomy["Revision"]["Color"]
}

plotting.plot_avg_distance()

#for i, project_id in enumerate(project_ids):
#  labels = data.get_label_stats(project_id)
#  plotting.overlay_distributions(labels, all_classes, "all", project_idx=i+1)

for project_idx, project_id in enumerate(project_ids):

  #real_idx = project_idx + 1
  #data.get_col_interconnectedness_score(project_id, "label", project_idx + 1, color_map)

  #data.visualize_labels(project_id)
  data.calculate_distribution_distances(project_id, project_idx, data.wasserstein_distance, "w_dist")

  #data.get_information_loss_from_aggregation(project_ids[project_idx])
  #data.calculate_distribution_distances(project_id, real_idx, data.wasserstein_distance, "w_dist")
  #data.calculate_distribution_distances(project_id, real_idx, data.jensen_shannon_divergence, "js_div")
  #data.calculate_distribution_distances(project_id, real_idx, data.bhattacharya_distance, "b_dist")
  #data.visualize_label_distributions(project_id, real_idx)

  #labels = data.get_label_stats(project_id)
  #plotting.overlay_distributions(labels, all_classes, "all", project_idx=project_idx+1)
  #plotting.overlay_distributions(labels, Taxonomy["Planning"]["Classes"], "Planning")

  #plotting.overlay_distributions(labels, Taxonomy["Implementation"]["Classes"], "Implementation")

  #plotting.overlay_distributions(labels, Taxonomy["Revision"]["Classes"], "Revision")

  #fname = f"distances_save/project_{project_idx + 1}_label_w_dist.csv"

  #plotting.plot_distance(fname, project_idx+1)

#get_average_annotation_label_step(project_ids[0])

#get_file_interconnectedness_score(project_ids[0])

#data = [get_writing_activities_occurances(x) for x in project_ids[:-1]]
#
#df = pd.DataFrame(data).T.fillna(0).astype(int)
#print(df.to_latex())

#word_diffs = [do_word_diff(x) for x in project_ids[:-1]]
#
#word_diff_df = pd.DataFrame(word_diffs).T.fillna(0).astype(int)
#print(word_diff_df.to_latex())

#for project_id in project_ids:
#  writing_activities_broad(project_id)
#  writing_activities_detailed(project_id)
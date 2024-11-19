Taxonomy = {
  "Planning": {
    "Classes": ("Idea Generation", "Idea Organization", "Section Planning"),
    "Color": "#EF9D65"
  },
  "Implementation": {
    "Classes": ("Text Production", "Object Insertion", "Cross-reference", "Citation Integration", "Macro Insertion"),
    "Color": "#84BCD1"
  },
  "Revision": {
    "Classes": ("Fluency", "Coherence", "Structural", "Clarity", "Linguistic Style", "Scientific Accuracy", "Visual Formatting"),
    "Color": "#9584D1"
  },
  "Other": {
    "Classes": ("Artifact", "No Label", "Ambiguous"),
    "Color": "#D1849A"
  }
}
RELEVANT_CLASSES = Taxonomy["Planning"]["Classes"] + Taxonomy["Implementation"]["Classes"] + Taxonomy["Revision"]["Classes"]

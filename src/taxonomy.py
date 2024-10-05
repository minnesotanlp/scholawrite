Taxonomy = {
  "Planning": {
    "Classes": ("Idea Generation", "Idea Organization", "Section Planning"),
    "Color": "#b0d184"
  },
  "Implementation": {
    "Classes": ("Text Production", "Object Insertion", "Cross-reference", "Citation Integration", "Macro Insertion"),
    "Color": "#84bcd1"
  },
  "Revision": {
    "Classes": ("Fluency", "Coherence", "Structural", "Clarity", "Textual Style", "Scientific Accuracy", "Visual Style"),
    "Color": "#9584d1"
  },
  "Other": {
    "Classes": ("Artifact", "No Label", "Ambiguous"),
    "Color": "#d1849a"
  }
}

RELEVANT_CLASSES = Taxonomy["Planning"]["Classes"] + Taxonomy["Implementation"]["Classes"] + Taxonomy["Revision"]["Classes"]
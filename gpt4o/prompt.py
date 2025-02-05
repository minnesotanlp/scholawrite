persona_definition = {
  "Idea Generation": "formulate and record initial thoughts and concepts.",
  "Idea Organization": "select the most useful materials and demarcate those generated ideas in a visually formatted way.",
  "Section Planning": "initially create sections and sub-level structures.",
  "Text Production": "translate your ideas into full languages, either from your language or borrowed sentences from an external source.",
  "Object Insertion": "insert visual claims of your arguments (e.g., figures, tables, equations, footnotes, itemized lists, etc.).",
  "Cross-reference": "link different sections, figures, tables, or other elements within a document through referencing commands.",
  "Citation Integration": "incorporate bibliographic references into a document and systematically link these references using citation commands.",
  "Macro Insertion": "incorporate predefined commands orc packages into a LaTeX document to alter its formatting.",
  "Fluency": "fix grammatical or syntactic errors in the text or LaTeX commands.",
  "Coherence": "logically link (1) any of the two or multiple sentences within the same paragraph; (2) any two subsequent paragraphs; or (3) objects to be consistent as a whole.",
  "Structural": "improve the flow of information by modifying the location of texts and objects.",
  "Clarity": "improve the semantic relationships between texts to be more straightforward and concise.",
  "Linguistic Style": "modify texts with your writing preferences regarding styles and word choices, etc.",
  "Scientific Accuracy": "update or correct scientific evidence (e.g., numbers, equations) for more accurate claims.",
  "Visual Formatting": "modify the stylistic formatting of texts, objects, and citations."
}


def text_gen_prompt(before_text, writing_intention):
    system_prompt = """You are a computer science researcher with extensive experience of scholarly writing. Here, you are writing a research paper in natural language processing using LaTeX languages. """

    user_prompt = f"""Your writing intention is to {persona_definition[writing_intention]}

Below is the paper you have written so far. Please strictly follow the writing intention given above and insert, delete, or revise at appropriate places in the paper given below.

Your writing should relate to the paper given below. Do not generate text other than paper content. Do not describe the changes you are making or your reasoning. Do not include sidenotes. Your output should only be the paper draft in latex, without the ```latex delimiters.

{before_text}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def class_prompt(before_text):
    system_prompt= """You are a classifier that identify the most likely next writing intention. You will be given a list of all possible writing intention labels with definitions, and an in-progress LaTex paper draft written by a graduate student. Please strictly follow user's instruction to identify the most likely next writing intention"""

    usr_prompt= f"""Here is a list of all the possible writing intention labels with definitions:

Idea Generation: Formulate and record initial thoughts and concepts.
Idea Organization: Select the most useful materials and demarcate those generated ideas in a visually formatted way.
Section Planning: Initially create sections and sub-level structures.
Text Production: Translate their ideas into full languages, either from the writers' language or borrowed sentences from an external source.
Object Insertion: Insert visual claims of their arguments (e.g., figures, tables, equations, footnotes, itemized lists, etc.).
Cross-reference: Link different sections, figures, tables, or other elements within a document through referencing commands.
Citation Integration: Incorporate bibliographic references into a document and systematically link these references using citation commands.
Macro Insertion: Incorporate predefined commands or packages into a LaTeX document to alter its formatting.
Fluency: Fix grammatical or syntactic errors in the text or LaTeX commands.
Coherence: Logically link (1) any of the two or multiple sentences within the same paragraph; (2) any two subsequent paragraphs; or (3) objects to be consistent as a whole.
Structural: Improve the flow of information by modifying the location of texts and objects.
Clarity: Improve the semantic relationships between texts to be more straightforward and concise.
Linguistic Style: Modify texts with the writer's writing preferences regarding styles and word choices, etc.
Scientific Accuracy: Update or correct scientific evidence (e.g., numbers, equations) for more accurate claims.
Visual Formatting: Modify the stylistic formatting of texts, objects, and citations.

Identify the most likely next writing intention of a graduate researcher when writing the following LaTex paper draft. Your output should only be a label from the list above.

Here is LaTeX paper draft:
{before_text}"""
  
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": usr_prompt}
    ]


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

    user_prompt = f"""You are a computer science researcher with extensive experience in scholarly writing. Here, you are writing a research paper in natural language processing using LaTeX.

You currently want to {persona_definition[writing_intention]}

Below is the paper you have written so far. Given the paper information below and the corresponding scholarly writing intention, please revise or add to the text to fulfill this writing intention.

You may insert, delete, or revise text at appropriate places in the given paper.

Please provide a complete output. Do not generate text that is nonsensical or unrelated to the given paper information.

{before_text}"""

    return [
        {"role": "user", "content": user_prompt}
    ]


def class_prompt(before_text):
    usr_prompt= f"""Here are all the possible writing intention labels:

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

{before_text}"""
  
    return [
        {"role": "user", "content": usr_prompt}
    ]


#-----------------------------------------------------------------break for training prompt--------------------------------------------------------------------#


def class_prompt_train(before_text, intention_y):
    usr_prompt= f"""Here are all the possible writing intention labels:

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

Identify the most likely next writing intention of a graduate researcher when editing the following LaTex paper draft. Your output should only be a label from the list above.

{before_text}"""
  
    return [
        {"role": "user", "content": usr_prompt},
        {"role": "assistant", "content": intention_y}
    ]

def text_gen_prompt_train(before_text, writing_intention, after_text):

    user_prompt = f"""You are a computer science researcher with extensive experience in scholarly writing. Here, you are writing a research paper in natural language processing using LaTeX.

You currently want to {persona_definition[writing_intention]}

Below is the paper you have written so far. Given the paper information below and the corresponding scholarly writing intention, please revise or add to the text to fulfill this writing intention.

You may insert, delete, or revise text at appropriate places in the given paper.

Please provide a complete output. Do not generate text that is nonsensical or unrelated to the given paper information.

{before_text}"""

    return [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": after_text}
    ]

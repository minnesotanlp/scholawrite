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

Identify the most likely next writing intention of a graduate researcher when editing the following LaTex paper draft. Your output should only be a label from the list above.

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
def add_special_tokens(tokenizer, classes=[]):
  tokenizer.add_tokens("<INPUT>")   # start input
  tokenizer.add_tokens("</INPUT>")  # end input
  tokenizer.add_tokens("<BT>")      # before text
  tokenizer.add_tokens("</BT>")     # before text
  tokenizer.add_tokens("<PWA>")     # start previous writing action
  tokenizer.add_tokens("</PWA>")    # end previous writing action
  tokenizer.add_tokens("<WI>")     # current writing intention
  tokenizer.add_tokens("</WI>")    # current writing intention
  tokenizer.add_tokens("<add>")
  tokenizer.add_tokens("</add>")
  tokenizer.add_tokens("<del>")
  tokenizer.add_tokens("</del>")
  tokenizer.add_tokens("<same>")
  tokenizer.add_tokens("</same>")

  for c in classes:
    tokenizer.add_tokens(f"<{c}>")
  
  tokenizer.add_special_tokens({'pad_token': '[PAD]'})    

  print("len", len(tokenizer))



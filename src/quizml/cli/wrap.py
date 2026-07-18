import re

def wrap_markdown(text, width=80):
    # Regexes for protected blocks (non-wrapping)
    block_patterns = [
        r"(?sm)^[ \t]*(?:`{3,}|~{3,}).*?^[ \t]*(?:`{3,}|~{3,})",
        r"(?sm)\$\$.*?\$\$",
        r"(?sm)\\\[.*?\\\]",
        r"(?sm)\\begin\{.*?\}.*?\\end\{.*?\}",
    ]
    
    inline_patterns = [
        r"(?s)\$.*?\$",          
        r"(?s)\\\(.*?\\\)",      
        r"(?s)!?\[.*?\]\(.*?\)", 
        r"(?s)`.*?`",            
    ]

    blocks = {}
    inlines = {}
    
    block_counter = 0
    inline_counter = 0
    
    def repl_block(m):
        nonlocal block_counter
        key = f"__BLOCK_{block_counter}__"
        blocks[key] = m.group(0)
        block_counter += 1
        return key

    def repl_inline(m):
        nonlocal inline_counter
        key = f"__INLINE_{inline_counter}__"
        inlines[key] = m.group(0)
        inline_counter += 1
        return key

    temp_text = text
    for pat in block_patterns:
        temp_text = re.sub(pat, repl_block, temp_text)
        
    # Split into paragraphs correctly
    lines = temp_text.split('\n')
    paragraphs = []
    current_p = []
    
    for line in lines:
        if re.match(r"^[ \t]*__BLOCK_\d+__[ \t]*$", line):
            if current_p: paragraphs.append('\n'.join(current_p)); current_p = []
            paragraphs.append(line)
        elif not line.strip():
            if current_p: paragraphs.append('\n'.join(current_p)); current_p = []
        elif re.match(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", line):
            if current_p: paragraphs.append('\n'.join(current_p)); current_p = []
            current_p.append(line)
        else:
            current_p.append(line)
    if current_p: paragraphs.append('\n'.join(current_p))
    
    wrapped_paragraphs = []
    
    for p in paragraphs:
        if not p.strip():
            continue
            
        if re.match(r"^[ \t]*__BLOCK_\d+__[ \t]*$", p):
            wrapped_paragraphs.append(p)
            continue
            
        if "\n|" in p or p.lstrip().startswith("|"):
            wrapped_paragraphs.append(p)
            continue
            
        lines_p = p.split('\n')
        first_line = lines_p[0]
        match = re.match(r"^([ \t]*(?:[-*+]|\d+\.)[ \t]+)", first_line)
        if match:
            subsequent_indent = " " * len(match.group(1))
        else:
            match_indent = re.match(r"^([ \t]+)", first_line)
            subsequent_indent = match_indent.group(1) if match_indent else ""
            
        p_temp = p
        for pat in inline_patterns:
            p_temp = re.sub(pat, repl_inline, p_temp)
            
        words = re.split(r'[ \t\n]+', p_temp.strip())
        wrapped_lines = []
        current_line = []
        current_len = 0
        
        for w in words:
            if not w: continue
            
            real_w = w
            for k, v in inlines.items():
                real_w = real_w.replace(k, v)
            w_len = len(real_w)
            
            if not current_line:
                current_line.append(w)
                current_len = w_len
            elif current_len + 1 + w_len <= width:
                current_line.append(w)
                current_len += 1 + w_len
            else:
                wrapped_lines.append(" ".join(current_line))
                current_line = [w]
                current_len = len(subsequent_indent) + w_len
                
        if current_line:
            wrapped_lines.append(" ".join(current_line))
            
        if wrapped_lines:
            for i in range(1, len(wrapped_lines)):
                wrapped_lines[i] = subsequent_indent + wrapped_lines[i]
                
        wrapped_paragraphs.append("\n".join(wrapped_lines))
        
    final_text = "\n\n".join(wrapped_paragraphs)
    
    for k, v in inlines.items():
        final_text = final_text.replace(k, v)
        
    for k, v in blocks.items():
        final_text = final_text.replace(k, v)
        
    return final_text

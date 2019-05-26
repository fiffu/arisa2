def codeblocked(s, lang=''):
    return f'```{lang}\n{s}```'

def make_two_cols(strings,
                  left_edge_width=0,
                  col_sep=3,
                  max_num_items=10,
                  max_col_width=None):
    """Forms card names into 2 cols, last cell item indicates excess length

    Takes a list of strings and joins them into two neatly-(mono)spaced
    columns. It's recommended you wrap the output in triple backticks (```)
    so these columns align nicely inside a Markdown code block.

    Args:
        strings: List[str]
        left_edge_width: int -- number of spaces used to pad the left margin
                                of the output block
        col_sep: int -- number of spaces used to separate the two columns
        max_col_width: int -- this does not include the left_edge and col_sep
    """
    def fix_length(slist, width=None):
        width = max_col_width or 100000
        return [
            s if len(s) < width else s[:width - 3] + '...'
            for s in slist
        ]

    left_edge_padding = ' ' * left_edge_width
    if len(strings) <= 3:
        return left_edge_padding + ('\n' + left_edge_padding).join(strings)

    if len(strings) > max_num_items:
        len_excess_rows = len(strings) - max_num_items - 1
        # Truncate to 10 items, replace last item with len(excess_rows)
        strings = strings[:max_num_items]
        strings[-1] = '(and {} others)'.format(len_excess_rows)

    # Cleave list; add modulo so odd-length list will be left-heavy:
    half = len(strings) // 2 + len(strings) % 2
    left, right = strings[:half], strings[half:]
    left_len = max(len(x) for x in left)
    right_len = max(len(y) for y in right)

    left = fix_length(left)
    right = fix_length(right)

    # Pad left-col words with space on their right using width format
    # Extra spaces on the right of the formatstring is for column spacing
    left_processed = ['{padding}{cell:<{width}}{intercol_space}'
                      .format(padding=left_edge_padding,
                              cell=entry,
                              intercol_space=' ' * col_sep,
                              width=left_len)
                      for entry in left]

    # Lazy to import itertools.zip_longest
    paired = []
    for i in range(len(left)):
        try:
            paired.append((left_processed[i], right[i]))
        except IndexError:
            paired.append((left_processed[i], ''))

    # Pair up and join rows
    return '\n'.join(x + y for x, y in paired)

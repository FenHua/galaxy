import itertools
import click

# http://stackoverflow.com/a/17462524/1097920
def block_width(block):
    try:
        return block.index('\n')
    except ValueError:
        return len(block)


def stack_str_blocks(blocks):
    """Takes a list of multiline strings, and stacks them horizontally.

    For example, given 'aaa\naaa' and 'bbbb\nbbbb', it returns
    'aaa bbbb\naaa bbbb'.  As in:

    'aaa  +  'bbbb   =  'aaa bbbb
     aaa'     bbbb'      aaa bbbb'

    Each block must be rectangular (all lines are the same length), but blocks
    can be different sizes.
    """
    builder = []
    block_lens = [block_width(bl) for bl in blocks]
    split_blocks = [bl.split('\n') for bl in blocks]

    for line_list in itertools.zip_longest(*split_blocks, fillvalue=None):
        for i, line in enumerate(line_list):
            if line is None:
                builder.append(' ' * block_lens[i])
            else:
                builder.append(line)
            if i != len(line_list) - 1:
                builder.append(' ')  # Padding
        builder.append('\n')

    return ''.join(builder[:-1])


def render_node(node):
    if not node.children:
        return str(node)

    child_strs = [child.display() for child in node.children]
    child_widths = [block_width(s) for s in child_strs]

    # How wide is this block?
    display_width = max(len(str(node)), sum(child_widths) + len(child_widths) - 1)

    # Determines midpoints of child blocks
    child_midpoints = []
    child_end = 0
    for width in child_widths:
        child_midpoints.append(child_end + (width // 2))
        child_end += width + 1

    # Builds up the brace, using the child midpoints
    brace_builder = []
    for i in range(display_width):
        if i < child_midpoints[0] or i > child_midpoints[-1]:
            brace_builder.append(' ')
        elif i in child_midpoints:
            brace_builder.append('+')
        else:
            brace_builder.append('-')
    brace = ''.join(brace_builder)

    name_str = '{:^{}}'.format(str(node), display_width)
    below = stack_str_blocks(child_strs)

    return name_str + '\n' + brace + '\n' + below



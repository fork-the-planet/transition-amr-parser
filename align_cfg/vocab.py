import collections
import json

from align_cfg.vocab_definitions import (
    PADDING_IDX, PADDING_TOK, BOS_IDX, BOS_TOK, EOS_IDX, EOS_TOK, special_tokens
)
from transition_amr_parser.io import read_amr2


def get_tokens(path, ibm_format=False, tokenize=False):
    local_tokens = set()
    local_graph_tokens = set()

    for amr in read_amr2(path, ibm_format=ibm_format, tokenize=tokenize):
        # surface tokens
        local_tokens.update(amr.tokens)
        # graph tokens
        for _, label, _ in amr.edges:
            local_graph_tokens.add(label)
        local_graph_tokens.update(amr.nodes.values())

    return local_tokens, local_graph_tokens


def main(args):

    summary = collections.defaultdict(list)

    settings = []
    settings.append((True, False))
    settings.append((False, False))
    settings.append((True, False))

    # collect information for all AMR
    tokens = set()
    graph_tokens = set()
    for amr_file in args.in_amrs:

        print('reading {}\n'.format(amr_file))

        for ibm_format, tokenize in settings:

            try:
                txt_toks, amr_toks = get_tokens(amr_file, ibm_format=True, tokenize=False)
                tokens = set.union(tokens, txt_toks)
                graph_tokens = set.union(graph_tokens, amr_toks)

                o = {}
                o['txt'] = len(txt_toks)
                o['amr'] = len(amr_toks)
                o['setting'] = (ibm_format, tokenize)
                o['success'] = True

                summary[amr_file].append(o)
                print(o)
            except Exception as e:
                o = {}
                o['setting'] = (ibm_format, tokenize)
                o['success'] = True

                summary[amr_file].append(o)
                print(o)
                print(e)

    graph_tokens.add('<NA>')
    graph_tokens.add('(')
    graph_tokens.add(')')
    for tok in special_tokens:
        if tok in tokens:
            tokens.remove(tok)
        if tok in graph_tokens:
            graph_tokens.remove(tok)

    # Add special symbols at the beginning
    # surface
    tokens = special_tokens + sorted(tokens)
    # graph
    # useful for linearized parse
    graph_tokens = special_tokens + sorted(graph_tokens)

    # print summary
    print('summary\n-------')

    for k, v in summary.items():
        print(k)
        for vv in v:
            print(vv)
        print('')

    print('writing...')

    # write files
    print('found {} text tokens'.format(len(tokens)))
    with open(args.out_text, 'w') as f:
        for tok in tokens:
            f.write(tok + '\n')
    print('found {} amr tokens'.format(len(graph_tokens)))
    with open(args.out_amr, 'w') as f:
        for tok in graph_tokens:
            f.write(tok + '\n')


if __name__ == '__main__':
    import argparse

    # Argument handling
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in-amrs", help="Read AMR files to determine vocabulary.",
        nargs='+', required=True)
    parser.add_argument(
        "--out-text", help="Output text vocab.",
        required=True)
    parser.add_argument(
        "--out-amr", help="Output amr vocab.",
        required=True)
    args = parser.parse_args()

    print(json.dumps(args.__dict__))

    main(args)

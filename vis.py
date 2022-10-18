from collections import OrderedDict
from ctypes import alignment
from macpath import join
import sys
from colorama import Fore, Back, Style
from transition_amr_parser.docamr_io import (
    AMR,
    read_amr
)
import docSmatch.smatch as docsmatch
import smatch_orig.smatch as orig_smatch
# from side_by_side import print_side_by_side
import pickle
from tqdm import tqdm
import os
from itertools import chain
from dictdiffer import diff as dictdiff
colors = {}
colors['terminal'] = {'red':f"{Fore.RED+Style.BRIGHT}",'blue':f"{Fore.BLUE+Style.BRIGHT}",'green':f"{Fore.GREEN+Style.BRIGHT}",'magenta':f"{Fore.MAGENTA+Style.BRIGHT}",'reset':f"{Style.RESET_ALL}"}
colors['html'] = {'red':'<span style="background-color:pink;font-weight:bold;"','blue':'<span style="background-color:cyan;font-weight:bold;"','green':'<span style="background-color:lime;font-weight:bold;"','purple':'<span style="background-color:#9ACD32;font-weight:bold;"','reset':'</span>'}
htmlclose='</div></body></html>'



    
def main(args): 
    # gold = read_amr(sys.argv[1]).values()
    
    gold = read_amr(args.f[1]).values()
    dev = read_amr(args.f[0]).values()
    f1 = open(args.f[0],'r')
    f2 = open(args.f[1],'r')
    # out_file = open('vis.out','w')

    if os.path.isfile('DATA/best_gold_to_pred_alignments_new_dict2_allalign_notokchk_origsmatch.pt'):
        pickle_file = open('DATA/best_gold_to_pred_alignments_new_dict2_allalign_notokchk_origsmatch.pt','rb')
        gold_to_pred_alignments = pickle.load(pickle_file)
    else:
        gold_to_pred_alignments = {'Alignments':[],'F1':[],'Coref-Score':[],'Orig_Smatch_Alignments':[]}
        for sent_num, (cur_amr1, cur_amr2) in tqdm(enumerate(orig_smatch.generate_amr_lines(f1, f2), start=1), desc='Getting Smatch alignments'):
            print("\n DOC ",sent_num)
            nums, ss,*a = docsmatch.get_amr_match(cur_amr1, cur_amr2,
                                            sent_num=sent_num,  # sentence number
                                            coref=True,get_alignment=True)
            # best_match_num, test_triple_num, gold_triple_num = nums
            # pr,re,f1_score = docsmatch.compute_f(best_match_num, test_triple_num, gold_triple_num)


            if args.orig_smatch:
                
                
                best_match_num, test_triple_num, gold_triple_num,*b = orig_smatch.get_amr_match(cur_amr1, cur_amr2,
                                                sent_num=sent_num,get_alignments=True)

                pr,re,f1_score = orig_smatch.compute_f(best_match_num, test_triple_num, gold_triple_num)
                
                # diff_in_align = { k : a[0][k] for k in set(a[0]) - set(b[0]) if a[0][k] is not None}
                
                
                # print("no. of diff node alignments between orig smatch and doc smatch ",len(diff_in_align))
                align_diff = list(dictdiff(a[0],b[0]))
                changed = 0
                removed = 0
                added = 0
                print(align_diff)
                for ad in align_diff:
                    if ad[0]=='change':
                        changed+=1
                    elif ad[0]=='remove':
                       removed += len([r for r in ad[2] if r[1] is not None]) 
                    elif ad[0]=='add':
                       added += len([r for r in ad[2] if r[1] is not None])
                print("no. changed ",changed)
                print("no. removed ",removed)
                print("no. added ",added)
                gold_to_pred_alignments['Orig_Smatch_Alignments'].append(b[0])
                
                
            subscores ={}
            for label in ss:
                if label in subscores:
                    subscores[label].update(ss[label])
                else:
                    subscores[label] = ss[label]
            co_num= subscores['Total Coref'].num
            co_tes = subscores['Total Coref'].pred_total
            co_gold = subscores['Total Coref'].gold_total
            co_pr,co_re,coref_score = docsmatch.compute_f(co_num,co_tes,co_gold)                            
            if len(a)>0:
               
                gold_to_pred_alignments['Alignments'].append(a[0])
            gold_to_pred_alignments['F1'].append(str(round(f1_score*100,2)))
            gold_to_pred_alignments['Coref-Score'].append(str(round(coref_score*100,2)))
        with open('DATA/best_gold_to_pred_alignments_new_dict2_allalign_notokchk_origsmatch.pt','wb') as pickle_file:
            pickle.dump(gold_to_pred_alignments,pickle_file)                                                       
    
    if args.output_html:
        htmlstr = '''
                    <html>
                    <head>
                    <style>
                    body {
                    margin: 0;
                    }

                    ul {
                    list-style-type: none;
                    margin: 0;
                    padding: 0;
                    width: 15%;
                    background-color: #f1f1f1;
                    position: fixed;
                    height: 100%;
                    overflow: auto;
                    }

                    li a {
                    display: block;
                    color: #000;
                    padding: 8px 16px;
                    text-decoration: none;
                    }

                    li a.active {
                    background-color: #04AA6D;
                    color: white;
                    }

                    li a:hover:not(.active) {
                    background-color: #555;
                    color: white;
                    }
                    </style>
                    </head>
                    <body>

                    <ul>
                    <li><a class="active" href="#home">Legend</a></li>
                    '''
        for i in range(0,len(gold)):
            htmlstr+='<li><a href="#doc_'+str(i)+'">Doc '+str(i)+'</a></li>'
        htmlstr+='''
                </ul>
                <div style="margin-left:15%;padding:1px 16px;height:1000px;">
                <h1 id="home">Coref chains in gold amr vs pred amr</h1>
                <h3> <span style="background-color:lime;">Green</span> : coref match (true positive) <br>
                    <span style="background-color:cyan;">Blue</span> : gold coref but not in pred (false negative) <br>
                    <span style="background-color:pink">Red</span> : pred coref but not in gold (false positive) <br>
                    <span style="background-color:#9ACD32">Yellow-Green</span> : gold and pred node alignments match but token alignments dont match <br>
                </h3>
                '''
        if not os.path.isdir('DATA/vis_output_html'):
                os.mkdir('DATA/vis_output_html')
        htmlfile = open("DATA/vis_output_html/corefchains_wnav_hover_newpred_corefscore_nodealign_notokchk_origsmatchalign.html","w")
        htmlfile.write(htmlstr)


    for num,(amr,amr2) in enumerate(zip(gold,dev)):
        print("DOC ",num)
        
        tokens = amr.tokens
        tokens2 = amr2.tokens
        coref_nodes = []
        coref_nodes2 = []
        for node in amr.nodes:
            if amr.nodes[node] == 'coref-entity':
                coref_nodes.append(node)
        
        for node in amr2.nodes:
            if amr2.nodes[node] == 'coref-entity':
                coref_nodes2.append(node)

        coref_chains = {}
        coref_chains2 = {}
        chain_nodes2 = {}
        chain_nodes = {}
        if args.output_html:
            htmldoc = '<h3 id=doc_'+str(num)+'>Doc '+str(num)+'</h4><br><h4>Smatch '+gold_to_pred_alignments['F1'][num]+'<br>Coref Score '+gold_to_pred_alignments['Coref-Score'][num]+'</h4>'
            htmldoc += '<br><h4>No. of gold coref chains '+str(len(coref_nodes))+'<br>No. of gold pred chains '+str(len(coref_nodes2))+'</h4>'
            htmlfile.write(htmldoc)
        print("No. of gold coref chains ",len(coref_nodes))
        print("No. of gold pred chains ",len(coref_nodes2))
        for cnode2 in coref_nodes2:
            coref_chains2[cnode2] = []
            chain_nodes2[cnode2] = []
            
            for e in amr2.edges:
                if e[0] not in amr2.nodes or e[2] not in amr2.nodes:
                    continue
                if e[1] == ':coref' and e[0] == cnode2:
                    if e[2] in amr2.alignments:
                        coref_chains2[cnode2].append(amr2.alignments[e[2]])
                        chain_nodes2[cnode2].append(e[2])
                    
                    

                if e[1] == ':coref-of' and e[2] == cnode2:
                    if e[0] in amr2.alignments:
                        coref_chains2[cnode2].append(amr2.alignments[e[0]])
                        chain_nodes2[cnode2].append(e[0])
                    
                    
        
        for cnode in coref_nodes:
            coref_chains[cnode] = []
            chain_nodes[cnode] = []
            

            for e in amr.edges:
                if e[0] not in amr.nodes or e[2] not in amr.nodes:
                    continue
                if e[1] == ':coref' and e[0] == cnode:
                    if e[2] in amr.alignments:
                        coref_chains[cnode].append(amr.alignments[e[2]])
                        chain_nodes[cnode].append(e[2])
                    
                if e[1] == ':coref-of' and e[2] == cnode:
                    if e[0] in amr.alignments:
                        coref_chains[cnode].append(amr.alignments[e[0]])
                        chain_nodes[cnode].append(e[0])
                    
                    
            outstr=""
            to_print_tokens = []
            to_print_cnodes = []
            to_print_predcnodes = []
            to_print2  = []
            pred_coref_node = None
            if cnode in gold_to_pred_alignments['Orig_Smatch_Alignments'][num]:
                pred_coref_node = gold_to_pred_alignments['Orig_Smatch_Alignments'][num][cnode]
            
               
            if args.different_doc:
                assert args.output_html is not True,'Not Implemented'
                raise NotImplementedError
                # for i,(tok,tok2) in enumerate(zip(tokens,tokens2)):
                #     is_chain = False
                #     if i in coref_chains[cnode]:
                #         # print(f"{Fore.RED+Style.BRIGHT}"+tok+f"{Style.RESET_ALL}", end=" ")
                #         to_print.append(f"{Fore.BLUE+Style.BRIGHT}"+tok+f"{Style.RESET_ALL}")
                #         is_chain = True
                #         # to_print.append(" ")
                #     else:
                #         #print(tok, end=" ")
                #         to_print.append(tok)
                #         # to_print.append(" ")
                #     if i in coref_chains2[pred_coref_node]:
                #         # print(f"{Fore.RED+Style.BRIGHT}"+tok+f"{Style.RESET_ALL}", end=" ")
                #         # CORRECT mattch with gold
                #         if is_chain:
                #             to_print2.append(f"{Fore.GREEN+Style.BRIGHT}"+tok+f"{Style.RESET_ALL}")
                #         else:
                #             to_print2.append(f"{Fore.RED+Style.BRIGHT}"+tok+f"{Style.RESET_ALL}")
                #         # to_print2.append(" ")
                #     else:
                #         #print(tok, end=" ")
                #         # MISSED COREF NODE
                #         # if is_chain:
                #         #     to_print2.append(f"{Fore.RED+Style.BRIGHT}"+tok2+f"{Style.RESET_ALL}")
                #         # else:
                #             to_print2.append(tok2)
                #         # to_print2.append(" ")
                
                # print_side_by_side(" ".join(to_print)," ".join(to_print2),col_padding=24, delimiter='|++++|')
            else:
                if args.output_html:
                    color_picker = colors['html']
                else:
                    color_picker = colors['terminal']
                
                if not args.node_alignment:
                    
                    for i,tok in enumerate(tokens):
                        is_chain = False
                        color = None
                        cnode_idx = None
                        pred_cnode_idx = None
                        #cnode presen in token alignment
                        cnode_ispresent=[i in aligns for aligns in coref_chains[cnode]]
                        if any(cnode_ispresent):
                            cnode_idx = cnode_ispresent.index(True)
                            
                            
                            is_chain = True
                            
                        
                        if pred_coref_node is not None:
                            pred_cnode_ispresent = [i in aligns for aligns in coref_chains2[pred_coref_node]]
                            if any(pred_cnode_ispresent):
                                pred_cnode_idx = pred_cnode_ispresent.index(True)
                                # CORRECT mattch with gold
                                if is_chain:
                                    color = color_picker['green']
                                    title =' title="gold:'+cnode+' pred:'+pred_coref_node+'">'
                                else:
                                    color = color_picker['red']
                                    title = ' title="pred:'+pred_coref_node+'">'
                            
                        if color is None:
                            
                            # MISSED COREF NODE
                            if is_chain:
                                color = color_picker['blue']
                                title = ' title="gold:'+cnode+'">'
                            else:
                                color = ''
                                title = ''
                        if cnode_idx is not None:
                            to_print_cnodes.append(color+'">'+amr.nodes[chain_nodes[cnode][cnode_idx]]+color_picker['reset']) 
                        if pred_cnode_idx is not None:
                            to_print_predcnodes.append(color+'">'+amr2.nodes[chain_nodes2[pred_coref_node][pred_cnode_idx]]+color_picker['reset'])   
                        to_print_tokens.append(color+title+tok+color_picker['reset'])
                else:
                    
                    green = {}
                    red  = {}
                    blue = {}
                    purple = {}
                    
                    
                    
                    if pred_coref_node in coref_chains2:
                        red = {ch_node2:coref_chains2[pred_coref_node][idx] for idx,ch_node2 in enumerate(chain_nodes2[pred_coref_node])}
                        
                    for idx,ch_node in enumerate(chain_nodes[cnode]):
                        
                        if ch_node in gold_to_pred_alignments['Orig_Smatch_Alignments'][num]:
                            pred_align_node = gold_to_pred_alignments['Orig_Smatch_Alignments'][num][ch_node]
                            if pred_align_node is not None and pred_align_node in red:
                                green[ch_node] = coref_chains[cnode][idx]
                                color = color_picker['green']
                                to_print_cnodes.append(color+'">'+amr.nodes[ch_node]+color_picker['reset'])
                                if red[pred_align_node]!= green[ch_node]:
                                    purple[pred_align_node] = red[pred_align_node]
                                    color = color_picker['purple']
                                    
                                # green[pred_align_node] = red[pred_align_node]
                                to_print_predcnodes.append(color+'">'+amr2.nodes[pred_align_node]+color_picker['reset'])
                                del red[pred_align_node]
                            else:
                                blue[ch_node] = coref_chains[cnode][idx]
                                color = color_picker['blue']
                                to_print_cnodes.append(color+'">'+amr.nodes[ch_node]+color_picker['reset'])

                    for red_node in red.keys():
                        color = color_picker['red'] 
                        to_print_predcnodes.append(color+'">'+amr2.nodes[red_node]+color_picker['reset'])

                    def flatten_list_of_lists(d):
                        return list(chain(*d.values()))

                    green_tokens = flatten_list_of_lists(green)
                    blue_tokens = flatten_list_of_lists(blue)
                    red_tokens = flatten_list_of_lists(red)
                    purple_tokens = flatten_list_of_lists(purple)

                    for i,tok in enumerate(tokens):
                        if i in green_tokens:
                            color = color_picker['green']
                            # ch_node = [j for j in green if i in green[j]]
                            title =' title="goldc:'+cnode+' predc:'+pred_coref_node+'">'
                        elif i in blue_tokens:
                            color = color_picker['blue']
                            title = ' title="goldc:'+cnode+'">'
                        elif i in red_tokens:
                            color = color_picker['red']
                            title = ' title="predc:'+pred_coref_node+'">'
                        elif i in purple_tokens:
                            color = color_picker['purple']
                            title = ' title="predc:'+pred_coref_node+'">'
                        else:
                            color = ''
                            title = ''
                        
                        to_print_tokens.append(color+title+tok+color_picker['reset'])
                    




                    

                
            if args.output_html:
                    htmlout = '<p>'+' '.join(to_print_tokens)+'</p>'
                    htmlout+='<p>Nodes corefed in gold '+' '.join(to_print_cnodes)+'</p>'
                    htmlout+='<p>Nodes corefed in pred '+ ' '.join(to_print_predcnodes if pred_coref_node in chain_nodes2 else ['No','smatch','alignment','between', 'gold', 'and','pred'])+color_picker['reset']+'</p><br><hr />'
                    
                    htmlfile.write(htmlout)
                    
                    
                    
            else:
                original_stdout = sys.stdout
                print(" ".join(to_print))
                
                
                print('\nNodes corefed in gold',f"{Fore.BLUE+Style.BRIGHT}"+' '.join(chain_nodes[cnode])+f"{Style.RESET_ALL}")
                print('Nodes corefed in pred',+' '.join(chain_nodes2[pred_coref_node] if pred_coref_node in chain_nodes2 else ' No nodes' )+f"{Style.RESET_ALL}")
                

                print("\n===============================")
                input("Press Enter to continue... \n")
        
    htmlfile.write(htmlclose)
    htmlfile.close()
    # out_file.close()
        

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DocAMR visualization")
    parser.add_argument(
        '-f',
        nargs=2,
        type=str,
        help=('Two files containing AMR pairs. '
              'AMRs in each file are separated by a single blank line'))
    
    parser.add_argument(
        '--different-doc',
        action='store_true',
        default=False,
        help='if two different docamrs (two different tokenized text) needs to be compared')

    parser.add_argument(
        '--output-html',
        action='store_true',
        default=True,
        help='if the output needs to be in html format'
    )
    parser.add_argument(
        '--node-alignment',
        action='store_true',
        default=True,
        help='if coloring method is based on node alignments instead of token alignments'
    )
    parser.add_argument(
        '--orig-smatch',
        action='store_true',
        default=True,
        help='if alignment is gotten from orig smatch insead of doc smatch'
    )

    args = parser.parse_args()
    main(args)
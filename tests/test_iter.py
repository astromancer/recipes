from recipes.iter import where
from recipes import op


list(where('akdjkjsdkmlvkmlvcl;ldl;dl;vds;l', 'ak'))

[0]

list(where('akdjkjsdkmlvkmlvcl;ldl;dl;vds;l', 'dl'))

[20, 23]

list(where('akdjkjsdkmlvkmlvcl;ldl;dl;vds;l', 'l'))

[10, 14, 17, 19, 21, 24, 30]

where('zzzzzzzzz', op.contained, '()')
[]
where('zzzzz()zzzz', op.contained, '()')
[6, 7]

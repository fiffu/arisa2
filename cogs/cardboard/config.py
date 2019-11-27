POSTS_PER_QUERY = 100 # Max is 100

DAN_COLOUR = 0xa4815e  # Brown


FEEDBACK = dict(
    no_results="I couldn't find any results with `{query}`. Try something else?"
    ,no_lewd_results="I couldn't find any results with `{}`. Maybe there's no lewd pictures for that?"
)


ALIASES = {
    'arisa_(shadowverse)':
        ['arisa']
    ,'minami_kotori':
        ['birb', 'bird']
    ,'shimamura_uzuki':
        ['dookie', 'duki']
    ,"annette_(king's_raid)":
        ['annette']
    ,'clarisse_(granblue_fantasy)':
        ['dokkan']
}


VETO = (
    'prinz',
    'cecilia'
)


SINKS = (
    '(cosplay)',
)


FLOATS = (
    "(king's_raid)",
    '(azur_lane)',
    '(granblue_fantasy)',
    '(fate/grand_order)',
    '(epic7)',
    '(shadowverse)',
    '(idolmaster)',
    '(crash_fever)',
    '(kantai_collection)',
)


EXCLUDE_POSTS_TAGGED_WITH = (
    'comic',
)


# Don't touch these, they're not settings, they're shared vars
DAN_URL_STUB = 'https://danbooru.donmai.us'
DAN_SEARCH_STUB = 'https://danbooru.donmai.us/posts?utf8=%E2%9C%93&tags='

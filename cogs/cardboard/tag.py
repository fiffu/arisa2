import logging
from typing import List, Mapping, Optional, Tuple

from . import config


log = logging.getLogger(__name__)


ALIASES: Mapping[str, List] = dict()

# Build inverse-index from actual->aliases to alias->actual
try:
    assert type(config.ALIASES) is dict
    for actual, alias_list in config.ALIASES.items():
        assert type(alias_list) is list
        for alias in alias_list:
            ALIASES[alias] = actual
            log.info(f'Loaded alias: {alias:>15} -> {actual}')

except AssertionError as e:
    log.error('bad config format for ALIASES')
    raise e


class Parser:
    default_parse_args = dict(
        resolve_aliases=True,
        spaces_to_underscore=False,
    )
    
    def __init__(self,
                 userinput: str = '',
                 resolve_aliases: Optional[bool] = None,
                 spaces_to_underscore: Optional[bool] = None):
        self.userinput = userinput
        self.parseargs = self.default_parse_args.copy()

        if resolve_aliases is not None:
            self.parseargs['resolve_aliases'] = resolve_aliases
        if spaces_to_underscore is not None:
            self.parseargs['spaces_to_underscore'] = spaces_to_underscore


    @classmethod
    def underscored(cls, string: str):
        return '_'.join(string.split())


    def parse(self, 
              userinput: str = '',
              **kwargs) -> Tuple[List[str], List[Tuple[str, str]]]:
        
        userinput = userinput or self.userinput
        if not userinput:
            raise ValueError('No userinput was provided')
        self.userinput = userinput
        
        # if hasattr(cls, '_parseargs')
        parseargs = self.parseargs.copy()
        for k, v in kwargs.items():
            if (k in parseargs) and (v is not None):
                parseargs[k] = v


        if parseargs['spaces_to_underscore']:
            userinput = self.underscored(userinput)

        candidates = []
        alias_applied: List[Tuple[str, str]] = []
        
        for token in userinput.split():
            if parseargs['resolve_aliases']:
                for alias, actual in ALIASES.items():
                    if alias in token:
                        token = userinput.replace(alias, actual)
                        alias_applied.append((alias, actual))
            candidates.append(token)

        return candidates, alias_applied

    
    @property
    def candidates(self) -> Tuple[List[str], Tuple[str, str]]:
        if not self.userinput:
            raise AttributeError('InputParser was not initialized with a '
                                 'userinput argument. Use InputParser.parse() '
                                 'instead')
        return self.parse()


    @property
    def first_candidate(self) -> Tuple[str, str, str]:
        cands, alias_applied = self.candidates
        cand = cands[0] if cands else None
        return cand, alias_applied

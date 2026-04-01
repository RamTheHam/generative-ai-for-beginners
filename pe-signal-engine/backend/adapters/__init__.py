from .apollo import ApolloAdapter
from .scrupp import ScruppAdapter
from .phantombuster import PhantomBusterAdapter
from .firecrawl import FirecrawlAdapter
from .linkedin_manual import LinkedInManualAdapter
from .boardex import BoardExAdapter
from .execatlas import ExecAtlasAdapter
from .affinity import AffinityAdapter

__all__ = [
    "ApolloAdapter",
    "ScruppAdapter",
    "PhantomBusterAdapter",
    "FirecrawlAdapter",
    "LinkedInManualAdapter",
    "BoardExAdapter",
    "ExecAtlasAdapter",
    "AffinityAdapter",
]

ADAPTER_REGISTRY: dict[str, type] = {
    "apollo": ApolloAdapter,
    "scrupp": ScruppAdapter,
    "phantombuster": PhantomBusterAdapter,
    "firecrawl": FirecrawlAdapter,
    "manual": LinkedInManualAdapter,
    "boardex": BoardExAdapter,
    "execatlas": ExecAtlasAdapter,
    "affinity": AffinityAdapter,
}

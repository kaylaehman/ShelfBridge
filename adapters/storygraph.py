"""StoryGraph CSV adapter.

StoryGraph imports the Goodreads CSV schema verbatim, so this only changes
identity and the output-path pref key (so it does not overwrite the Goodreads
file when both are exported). The row mapping is inherited unchanged.
"""
from calibre_plugins.shelf_bridge.adapters.goodreads import GoodreadsAdapter


class StoryGraphAdapter(GoodreadsAdapter):
    service_id = "storygraph"
    display_name = "StoryGraph CSV"
    path_pref = "storygraph_output_path"

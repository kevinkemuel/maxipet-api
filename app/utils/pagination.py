from typing import List, TypeVar, Generic
from math import ceil
from app.schemas import PaginatedResponse

T = TypeVar('T')

class Paginator(Generic[T]):
    """Helper class for pagination"""
    
    def __init__(self, items: List[T], total: int, page: int, limit: int):
        self.items = items
        self.total = total
        self.page = page
        self.limit = limit
        self.pages = ceil(total / limit) if limit > 0 else 0
    
    def to_response(self) -> PaginatedResponse:
        """Convert to paginated response schema"""
        return PaginatedResponse(
            items=[item.dict() if hasattr(item, 'dict') else item for item in self.items],
            total=self.total,
            page=self.page,
            limit=self.limit,
            pages=self.pages
        )

def paginate(items: List[T], page: int, limit: int) -> Paginator[T]:
    """Paginate a list of items"""
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]
    
    return Paginator(
        items=paginated_items,
        total=total,
        page=page,
        limit=limit
    )

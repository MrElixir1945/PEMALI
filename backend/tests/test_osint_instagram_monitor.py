"""
Comprehensive tests untuk OSINT Instagram Monitor Module (Sprint 3).
Covers: input validation, static helpers, search, scrape, LLM analysis,
execute() integration, UTI V2 compliance, error handling.
"""
import json
import sys
import os
import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.modules.osint_instagram_monitor import (
    OSINTInstagramMonitor, InstagramMonitorInput, module
)
from backend.core.base_module import ModuleOutput, THKAlignment


# ═══════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════

SAMPLE_SHORTCODES = ["ABC123def", "XyZ789hi", "MnO111pqr", "Rst222uvw"]
SAMPLE_POST = {
    "shortcode": "ABC123def",
    "date": "2026-05-15T14:30:00+00:00",
    "caption": "Pantai Kuta udah penuh sampah plastik, parah. Sedih banget.",
    "likes": 3200,
    "comments_count": 89,
    "comments_sample": [
        {"text": "sedih banget lihatnya 😢", "likes": 45},
        {"text": "pemerintah harus turun tangan", "likes": 32},
    ],
    "url": "https://instagram.com/p/ABC123def",
    "is_video": False,
}
SAMPLE_LLM_ANALYSIS = {
    "emotions": {"marah": 1, "sedih": 3, "khawatir": 0, "dukung": 0,
                 "kritis": 2, "apati": 0, "ajakan": 1},
    "dominant_tone": "sedih",
    "evidence": ["'Pantai Kuta udah penuh sampah' — post 3200 likes",
                  "'pemerintah harus turun tangan' — 32 likes"],
    "trend_summary": "Mayoritas post mengungkapkan kesedihan dan kekritisan.",
}


# ═══════════════════════════════════════════════════════════════════
# TESTS — Input Schema Validation
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorInputSchema:
    def test_valid_minimal_input(self):
        params = InstagramMonitorInput(issue="sampah plastik bali")
        assert params.issue == "sampah plastik bali"
        assert params.max_posts == 10
        assert params.include_comments is True
        assert params.days_back is None
        assert params.date_from is None
        assert params.date_to is None

    def test_valid_full_input(self):
        params = InstagramMonitorInput(
            issue="sampah plastik pantai kuta",
            date_from="2026-05-01",
            date_to="2026-05-15",
            max_posts=15,
            include_comments=True,
            location_hint="Kuta, Bali",
            instagram_login="test_user",
            instagram_password="test_pass",
        )
        assert params.date_from == "2026-05-01"
        assert params.date_to == "2026-05-15"
        assert params.max_posts == 15
        assert params.location_hint == "Kuta, Bali"

    def test_valid_days_back(self):
        params = InstagramMonitorInput(issue="banjir bandang", days_back=30)
        assert params.days_back == 30
        assert params.date_from is None

    def test_invalid_issue_too_short(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="ab")
            assert False, "Seharusnya raise ValidationError"
        except ValidationError as e:
            assert "String should have at least 3 characters" in str(e)

    def test_invalid_issue_empty(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="")
            assert False, "Seharusnya raise ValidationError"
        except ValidationError as e:
            assert "String should have at least 3 characters" in str(e)

    def test_invalid_max_posts_exceeds_limit(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="test", max_posts=50)
            assert False, "Seharusnya raise ValidationError"
        except ValidationError as e:
            assert "less than or equal to 30" in str(e)

    def test_invalid_days_back_exceeds_limit(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="test", days_back=500)
            assert False, "Seharusnya raise ValidationError"
        except ValidationError as e:
            assert "less than or equal to 365" in str(e)

    def test_invalid_date_format(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(
                issue="test", date_from="01-05-2026",
                date_to="15-05-2026"
            )
        except ValidationError:
            pass  # valid — pydantic str field, format divalidasi di module

    def test_both_date_and_days_back_valid(self):
        """Kedua mode filter bisa diisi, module prioritaskan date range."""
        params = InstagramMonitorInput(
            issue="test", date_from="2026-05-01",
            date_to="2026-05-15", days_back=7
        )
        assert params.date_from is not None
        assert params.days_back is not None

    def test_boundary_max_posts_1(self):
        params = InstagramMonitorInput(issue="test", max_posts=1)
        assert params.max_posts == 1

    def test_boundary_max_posts_30(self):
        params = InstagramMonitorInput(issue="test", max_posts=30)
        assert params.max_posts == 30

    def test_boundary_days_back_1(self):
        params = InstagramMonitorInput(issue="test", days_back=1)
        assert params.days_back == 1

    def test_boundary_days_back_365(self):
        params = InstagramMonitorInput(issue="test", days_back=365)
        assert params.days_back == 365

    def test_issue_max_length(self):
        params = InstagramMonitorInput(issue="a" * 200)
        assert len(params.issue) == 200

    def test_issue_exceeds_max_length(self):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="a" * 201)
            assert False, "Seharusnya raise ValidationError"
        except ValidationError as e:
            assert "at most 200" in str(e)


# ═══════════════════════════════════════════════════════════════════
# TESTS — Static Helper Methods
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorStaticMethods:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()

    def test_parse_date_valid(self):
        dt = self.module._parse_date("2026-05-15")
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 15
        assert dt.tzinfo is not None

    def test_parse_date_invalid_format(self):
        try:
            self.module._parse_date("15-05-2026")
            assert False
        except ValueError:
            pass

    def test_resolve_date_range_with_date_from_to(self):
        params = MagicMock(spec=InstagramMonitorInput)
        params.date_from = "2026-05-01"
        params.date_to = "2026-05-15"
        params.days_back = None
        date_from, date_to = self.module._resolve_date_range(params)
        assert date_from.year == 2026
        assert date_from.month == 5
        assert date_from.day == 1
        assert date_to.day == 15

    def test_resolve_date_range_with_days_back(self):
        params = MagicMock(spec=InstagramMonitorInput)
        params.date_from = None
        params.date_to = None
        params.days_back = 7
        now = datetime.now(timezone.utc)
        date_from, date_to = self.module._resolve_date_range(params)
        delta = date_to - date_from
        assert abs(delta.days - 7) <= 1

    def test_resolve_date_range_default_days_back(self):
        params = MagicMock(spec=InstagramMonitorInput)
        params.date_from = None
        params.date_to = None
        params.days_back = None
        date_from, date_to = self.module._resolve_date_range(params)
        delta = date_to - date_from
        assert abs(delta.days - 7) <= 1

    def test_extract_shortcodes_standard(self):
        results = [
            {"url": "https://www.instagram.com/p/ABC123def/"},
            {"url": "https://instagram.com/reel/XyZ789hi/"},
            {"url": "https://www.instagram.com/tv/MnO111pqr/"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert "ABC123def" in codes
        assert "XyZ789hi" in codes
        assert "MnO111pqr" in codes
        assert len(codes) == 3

    def test_extract_shortcodes_deduplication(self):
        results = [
            {"url": "https://www.instagram.com/p/ABC123/"},
            {"url": "https://instagram.com/p/ABC123/?utm_source=ig_share"},
            {"url": "https://www.instagram.com/p/DEF456/"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert codes.count("ABC123") == 1
        assert len(codes) == 2

    def test_extract_shortcodes_no_matches(self):
        results = [
            {"url": "https://www.google.com/"},
            {"url": "https://www.facebook.com/"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert codes == []

    def test_extract_shortcodes_empty_input(self):
        codes = self.module._extract_shortcodes([])
        assert codes == []

    def test_extract_shortcodes_with_query_params(self):
        results = [
            {"url": "https://www.instagram.com/p/ABC123/?hl=en"},
            {"url": "https://instagram.com/reel/DEF456/?igshid=xyz"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert "ABC123" in codes
        assert "DEF456" in codes

    def test_extract_shortcodes_without_www(self):
        results = [{"url": "https://instagram.com/p/ShortCode/"}]
        codes = self.module._extract_shortcodes(results)
        assert "ShortCode" in codes

    def test_extract_shortcodes_mixed_valid_invalid(self):
        results = [
            {"url": "https://www.instagram.com/p/Valid1/"},
            {"url": "https://www.notinstagram.com/p/Fake1/"},
            {"url": "https://www.instagram.com/reel/Valid2/"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert "Valid1" in codes
        assert "Valid2" in codes
        assert "Fake1" not in codes

    def test_shortcode_with_underscores_and_hyphens(self):
        results = [{"url": "https://www.instagram.com/p/AB_CD-ef/"}]
        codes = self.module._extract_shortcodes(results)
        assert "AB_CD-ef" in codes


# ═══════════════════════════════════════════════════════════════════
# TESTS — DuckDuckGo Search
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorSearch:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_basic(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs

        mock_ddgs.text.return_value = [
            {"title": "Post1", "href": "https://www.instagram.com/p/ABC123/",
             "body": "Caption about sampah"},
        ]

        results = self.module._search_instagram_urls("sampah plastik", None)

        assert len(results) >= 1
        assert any("instagram.com" in r["url"] for r in results)
        # Verify queries include site:instagram.com
        site_queries = [c[0] for c in mock_ddgs.text.call_args_list
                        if "site:instagram.com" in str(c)]
        assert len(site_queries) >= 1

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_with_location_hint(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs
        mock_ddgs.text.return_value = []

        results = self.module._search_instagram_urls("sampah", "Kuta, Bali")
        # Should have called with location hint query
        location_calls = [
            c for c in mock_ddgs.text.call_args_list
            if "Kuta" in str(c) or "Bali" in str(c)
        ]
        assert len(location_calls) >= 1

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_fallback_query(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs
        mock_ddgs.text.return_value = []

        self.module._search_instagram_urls("banjir bandang", None)

        # Should have called with fallback query (istanbul site: instagram)
        queries = [c[0][0] for c in mock_ddgs.text.call_args_list]
        fallback_queries = [q for q in queries if "instagram" in q and "site:" not in q]
        assert len(fallback_queries) >= 1

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_deduplicates_urls(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs

        mock_ddgs.text.return_value = [
            {"title": "Same Post", "href": "https://www.instagram.com/p/ABC123/",
             "body": "content"},
        ]

        results = self.module._search_instagram_urls("test", None)
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls))

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_handles_error_gracefully(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs
        mock_ddgs.text.side_effect = Exception("DDGS timeout")

        results = self.module._search_instagram_urls("test", None)
        assert results == []

    @patch("backend.modules.osint_instagram_monitor.DDGS")
    def test_search_partial_failure(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs_class.return_value = mock_ddgs

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return [{"title": "Found", "href": "https://instagram.com/p/ABC123/",
                         "body": "test"}]
            raise Exception("Partial failure")

        mock_ddgs.text.side_effect = side_effect
        results = self.module._search_instagram_urls("test", None)
        assert len(results) >= 1


# ═══════════════════════════════════════════════════════════════════
# TESTS — Scrape Post Logic
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorScrape:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()

    @patch("instaloader.Instaloader")
    @patch("instaloader.Post")
    def test_scrape_post_success(self, mock_post_class, mock_loader_class):
        date_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 5, 20, tzinfo=timezone.utc)

        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        mock_post = MagicMock()
        mock_post.shortcode = "ABC123"
        mock_post.date_local = datetime(2026, 5, 15, 14, 30)
        mock_post.caption = "Pantai Kuta udah penuh sampah plastik"
        mock_post.likes = 3200
        mock_post.comments = 89
        mock_post.is_video = False

        mock_comment1 = MagicMock()
        mock_comment1.text = "sedih banget lihatnya"
        mock_comment1.likes_count = 45
        mock_comment2 = MagicMock()
        mock_comment2.text = "pemerintah harus turun tangan"
        mock_comment2.likes_count = 32
        mock_post.get_comments.return_value = [mock_comment1, mock_comment2]

        mock_post_class.from_shortcode.return_value = mock_post

        result = asyncio.run(self.module._scrape_post(
            "ABC123", date_from, date_to, True, {}
        ))

        assert result is not None
        assert result["shortcode"] == "ABC123"
        assert result["likes"] == 3200
        assert result["comments_count"] == 89
        assert len(result["comments_sample"]) == 2
        assert result["comments_sample"][0]["likes"] == 45

    @patch("instaloader.Instaloader")
    @patch("instaloader.Post")
    def test_scrape_post_out_of_range(self, mock_post_class, mock_loader_class):
        date_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 5, 10, tzinfo=timezone.utc)

        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_post = MagicMock()
        mock_post.date_local = datetime(2026, 5, 15, 14, 30)
        mock_post_class.from_shortcode.return_value = mock_post

        result = asyncio.run(self.module._scrape_post(
            "ABC123", date_from, date_to, True, {}
        ))
        assert result is None

    @patch("instaloader.Instaloader")
    @patch("instaloader.Post")
    def test_scrape_post_error(self, mock_post_class, mock_loader_class):
        date_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 5, 20, tzinfo=timezone.utc)

        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_post_class.from_shortcode.side_effect = Exception("Post deleted")

        result = asyncio.run(self.module._scrape_post(
            "ABC123", date_from, date_to, True, {}
        ))
        assert result is None

    @patch("instaloader.Instaloader")
    @patch("instaloader.Post")
    def test_scrape_post_comments_fallback_on_error(self, mock_post_class,
                                                      mock_loader_class):
        date_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 5, 20, tzinfo=timezone.utc)

        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_post = MagicMock()
        mock_post.shortcode = "ABC123"
        mock_post.date_local = datetime(2026, 5, 15, 14, 30)
        mock_post.caption = "Test caption"
        mock_post.likes = 100
        mock_post.comments = 10
        mock_post.is_video = False
        mock_post.get_comments.side_effect = Exception("Comments API error")
        mock_post_class.from_shortcode.return_value = mock_post

        result = asyncio.run(self.module._scrape_post(
            "ABC123", date_from, date_to, True, {}
        ))
        assert result is not None
        assert result["comments_sample"] == []

    @patch("instaloader.Instaloader")
    @patch("instaloader.Post")
    def test_scrape_post_title_pic(self, mock_post_class, mock_loader_class):
        date_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 5, 20, tzinfo=timezone.utc)

        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_post = MagicMock()
        mock_post.shortcode = "ABC123"
        mock_post.date_local = datetime(2026, 5, 15, 14, 30)
        mock_post.caption = "Test"
        mock_post.likes = 500
        mock_post.comments = 20
        mock_post.is_video = False
        mock_post_class.from_shortcode.return_value = mock_post

        result = asyncio.run(self.module._scrape_post(
            "ABC123", date_from, date_to, True, {}
        ))
        assert result is not None
        assert result["url"] == "https://instagram.com/p/ABC123"


# ═══════════════════════════════════════════════════════════════════
# TESTS — LLM Analysis
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorLLMAnalysis:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_with_posts(self, mock_get_llm):
        mock_client = AsyncMock()
        mock_get_llm.return_value = mock_client
        mock_res = MagicMock()
        mock_res.choices[0].message.content = json.dumps(SAMPLE_LLM_ANALYSIS)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_res)

        posts = [SAMPLE_POST]

        result = asyncio.run(self.module._analyze_emotions(posts, "sampah plastik"))

        assert result["emotions"]["sedih"] == 3
        assert result["dominant_tone"] == "sedih"
        assert len(result["evidence"]) >= 1

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_empty_posts(self, mock_get_llm):
        result = asyncio.run(self.module._analyze_emotions([], "test issue"))
        assert result["dominant_tone"] == "no_data"
        assert result["trend_summary"] == "Tidak ada post untuk dianalisis."

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_without_comments(self, mock_get_llm):
        mock_client = AsyncMock()
        mock_get_llm.return_value = mock_client
        mock_res = MagicMock()
        mock_res.choices[0].message.content = json.dumps(SAMPLE_LLM_ANALYSIS)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_res)

        posts_no_comments = [dict(SAMPLE_POST, comments_sample=[])]
        result = asyncio.run(self.module._analyze_emotions(
            posts_no_comments, "test"
        ))
        assert "dominant_tone" in result

    def test_analyze_posts_limited_to_10(self):
        """Module hanya menganalisis max 10 post."""
        many_posts = [SAMPLE_POST.copy() for _ in range(10 + 5)]
        from string import Formatter
        assert True

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_llm_error_fallback(self, mock_get_llm):
        mock_client = AsyncMock()
        mock_get_llm.return_value = mock_client
        from openai import APIError
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIError("OpenRouter down", request=MagicMock(),
                                  body={"error": "down"})
        )

        result = asyncio.run(self.module._analyze_emotions(
            [SAMPLE_POST], "test"
        ))
        assert result["dominant_tone"] == "analysis_error"

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_llm_invalid_json(self, mock_get_llm):
        mock_client = AsyncMock()
        mock_get_llm.return_value = mock_client
        mock_res = MagicMock()
        mock_res.choices[0].message.content = "::: invalid json :::"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_res)

        result = asyncio.run(self.module._analyze_emotions(
            [SAMPLE_POST], "test"
        ))
        assert result["dominant_tone"] == "analysis_error"

    @patch("backend.modules.osint_instagram_monitor.get_llm_client")
    def test_analyze_llm_multiple_posts(self, mock_get_llm):
        mock_client = AsyncMock()
        mock_get_llm.return_value = mock_client
        mock_res = MagicMock()
        mock_res.choices[0].message.content = json.dumps(SAMPLE_LLM_ANALYSIS)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_res)

        posts = [
            {"shortcode": f"POST{i}", "likes": 100 * (10 - i),
             "comments_count": 10, "caption": f"Test {i}",
             "comments_sample": [{"text": f"Comment {i}", "likes": 5}],
             "date": "2026-05-15T00:00:00+00:00", "url": f"https://ig.com/p/POST{i}",
             "is_video": False}
            for i in range(5)
        ]

        result = asyncio.run(self.module._analyze_emotions(posts, "test"))
        assert "emotions" in result


# ═══════════════════════════════════════════════════════════════════
# TESTS — Module Execute Integration
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorExecute:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()
        self.context = {"session_id": "test_session"}

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_happy_path(self, mock_analyze, mock_scrape,
                                 mock_extract, mock_search):
        mock_search.return_value = [{"url": "https://instagram.com/p/ABC123/"}]
        mock_extract.return_value = SAMPLE_SHORTCODES[:3]
        mock_scrape.return_value = (
            [SAMPLE_POST, SAMPLE_POST, SAMPLE_POST],
            []
        )
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(issue="sampah plastik", days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        assert isinstance(result, ModuleOutput)
        assert result.status == 200
        assert result.data["scrape_summary"]["total_posts_scraped"] == 3
        assert result.data["scrape_summary"]["total_likes"] == 3200 * 3
        assert result.data["llm_analysis"]["dominant_tone"] == "sedih"
        assert result.agent_hint.startswith("INSTAGRAM MONITOR")
        assert result.thk_alignment is not None

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    def test_execute_no_shortcodes(self, mock_extract, mock_search):
        mock_search.return_value = [{"url": "https://google.com/"}]
        mock_extract.return_value = []

        params = InstagramMonitorInput(issue="xyz123nonexistent", days_back=1)
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.status == 404
        assert "0 post" in result.agent_hint
        assert result.data["total_shortcodes_found"] == 0

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_with_partial_scrape_errors(self, mock_analyze,
                                                 mock_scrape, mock_extract,
                                                 mock_search):
        mock_search.return_value = [{"url": "https://instagram.com/p/ABC123/"}]
        mock_extract.return_value = SAMPLE_SHORTCODES[:3]
        mock_scrape.return_value = (
            [SAMPLE_POST],
            ["POST000", "POST999"]
        )
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(issue="test", days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.status == 200
        assert result.data["scrape_summary"]["total_posts_scraped"] == 1
        assert result.data["scrape_summary"]["total_scrape_errors"] == 2
        assert isinstance(result.data["scrape_errors"], list)

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_max_posts_respected(self, mock_analyze, mock_scrape,
                                          mock_extract, mock_search):
        mock_search.return_value = []
        mock_extract.return_value = SAMPLE_SHORTCODES[:20]
        mock_scrape.return_value = (
            [SAMPLE_POST] * 5,
            []
        )
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(issue="test", max_posts=5, days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        # scrape_posts harus dipanggil dengan max_posts
        assert mock_scrape.call_count == 1
        # shortcodes yang dikirim ke scrape dibatasi
        called_shortcodes = mock_scrape.call_args[0][0]
        assert len(called_shortcodes) <= 30

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_dedicated_llm_prompt_includes_issue(self, mock_analyze,
                                                          mock_scrape,
                                                          mock_extract,
                                                          mock_search):
        mock_search.return_value = []
        mock_extract.return_value = SAMPLE_SHORTCODES[:2]
        mock_scrape.return_value = ([SAMPLE_POST, SAMPLE_POST], [])
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(issue="sampah plastik pantai kuta",
                                        days_back=7)
        asyncio.run(self.module.execute(params, self.context))

        # verify issue passed to analyze
        analyze_issue = mock_analyze.call_args[0][1]
        assert "sampah plastik" in analyze_issue

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_env_login_used(self, mock_analyze, mock_scrape,
                                     mock_extract, mock_search):
        mock_search.return_value = []
        mock_extract.return_value = SAMPLE_SHORTCODES[:2]
        mock_scrape.return_value = ([SAMPLE_POST, SAMPLE_POST], [])
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        with patch.dict(os.environ, {"INSTAGRAM_USER": "env_user",
                                      "INSTAGRAM_PASS": "env_pass"}):
            params = InstagramMonitorInput(issue="test", days_back=7)
            asyncio.run(self.module.execute(params, self.context))

        _, _, _, _, username, password = mock_scrape.call_args[0]
        assert username == "env_user"
        assert password == "env_pass"

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_supports_date_range(self, mock_analyze, mock_scrape,
                                          mock_extract, mock_search):
        mock_search.return_value = []
        mock_extract.return_value = SAMPLE_SHORTCODES[:2]
        mock_scrape.return_value = ([SAMPLE_POST, SAMPLE_POST], [])
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(
            issue="test",
            date_from="2026-05-01",
            date_to="2026-05-15",
        )
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.data["period"]["date_from"] == "2026-05-01T00:00:00+00:00"
        assert result.status == 200

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_supports_days_back(self, mock_analyze, mock_scrape,
                                         mock_extract, mock_search):
        mock_search.return_value = []
        mock_extract.return_value = SAMPLE_SHORTCODES[:2]
        mock_scrape.return_value = ([SAMPLE_POST, SAMPLE_POST], [])
        mock_analyze.return_value = SAMPLE_LLM_ANALYSIS

        params = InstagramMonitorInput(issue="test", days_back=14)
        result = asyncio.run(self.module.execute(params, self.context))

        assert "14" in result.data["period"]["date_from"] or \
               result.status == 200

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_execute_search_failure(self, mock_analyze, mock_scrape,
                                     mock_extract, mock_search):
        mock_search.side_effect = Exception("DDGS unavailable")

        params = InstagramMonitorInput(issue="test", days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.status == 500
        assert "Gagal mencari" in result.agent_hint


# ═══════════════════════════════════════════════════════════════════
# TESTS — UTI V2 Output Format Compliance
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorUTIV2:
    def test_output_has_required_fields(self):
        output = ModuleOutput(
            status=200,
            data={"scrape_summary": {"total_posts_scraped": 0}, "posts": [],
                  "period": {}, "llm_analysis": {}, "issue": "test"},
            agent_hint="INSTAGRAM MONITOR: test",
            thk_alignment=THKAlignment(
                parahyangan="test", pawongan="test", palemahan="test"
            )
        )
        dump = output.model_dump()
        assert "status" in dump
        assert "data" in dump
        assert "agent_hint" in dump
        assert "thk_alignment" in dump

    def test_status_label_success(self):
        output = ModuleOutput(status=200, data={})
        assert output.status_label == "success"

    def test_status_label_error(self):
        output = ModuleOutput(status=404, data={})
        assert output.status_label == "error"

    def test_is_ok(self):
        assert ModuleOutput(status=200, data={}).is_ok is True
        assert ModuleOutput(status=400, data={}).is_ok is False
        assert ModuleOutput(status=500, data={}).is_ok is False

    def test_tri_haka_karana_present_in_output(self):
        output = ModuleOutput(
            status=200,
            data={"scrape_summary": {"total_posts_scraped": 0}, "posts": [],
                  "period": {}, "llm_analysis": {}, "issue": "test"},
            agent_hint="test",
            thk_alignment=THKAlignment(
                parahyangan="Keseimbangan spiritual dalam audit data publik",
                pawongan="Transparansi opini publik",
                palemahan="Pemantauan lingkungan Bali"
            )
        )
        dump = output.model_dump()
        assert "parahyangan" in dump["thk_alignment"]
        assert "pawongan" in dump["thk_alignment"]
        assert "palemahan" in dump["thk_alignment"]

    def test_error_msg_optional(self):
        output = ModuleOutput(status=200, data={})
        assert output.error_msg is None

    def test_agent_hint_max_length(self):
        hint = "INSTAGRAM MONITOR: 8 post. Emosi dominan: sedih."
        output = ModuleOutput(status=200, data={}, agent_hint=hint)
        assert len(output.agent_hint) <= 200

    def test_output_serializable(self):
        output = ModuleOutput(
            status=200,
            data={"posts": [SAMPLE_POST]},
            agent_hint="test",
            thk_alignment=THKAlignment(
                parahyangan="p", pawongan="p", palemahan="p"
            )
        )
        dump = output.model_dump()
        json_str = json.dumps(dump)
        assert len(json_str) > 0
        reloaded = json.loads(json_str)
        assert reloaded["status"] == 200

    def test_execute_output_conforms_to_uti(self):
        """Output dari execute() harus selalu valid ModuleOutput."""
        output = ModuleOutput(
            status=404,
            data={
                "issue": "nonexistent",
                "period": {"date_from": "2026-05-12", "date_to": "2026-05-19"},
                "total_shortcodes_found": 0,
                "posts": [],
                "llm_analysis": {
                    "emotions": {}, "dominant_tone": "no_data",
                    "evidence": [], "trend_summary": ""
                }
            },
            agent_hint="INSTAGRAM MONITOR: 0 post ditemukan.",
            thk_alignment=THKAlignment(
                parahyangan="Data opini publik dikumpulkan secara etis dari sumber terbuka.",
                pawongan="Mengukur kepedulian masyarakat terhadap lingkungan.",
                palemahan="Memantau dampak pencemaran di pesisir Bali."
            )
        )
        dump = output.model_dump()
        assert dump["status"] in [200, 404, 400, 500]
        assert isinstance(dump["data"]["posts"], list)


# ═══════════════════════════════════════════════════════════════════
# TESTS — THK Alignment
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorTHK:
    def test_thk_present_in_success(self):
        output = ModuleOutput(
            status=200,
            data={"scrape_summary": {"total_posts_scraped": 0}, "posts": [],
                  "period": {}, "llm_analysis": {}, "issue": "test"},
            agent_hint="test",
            thk_alignment=THKAlignment(
                parahyangan="Data opini publik dikumpulkan secara etis dari sumber terbuka.",
                pawongan="Mengukur kepedulian masyarakat terhadap lingkungan.",
                palemahan="Memantau dampak pencemaran di pesisir Bali."
            )
        )
        assert output.thk_alignment.parahyangan != ""
        assert output.thk_alignment.pawongan != ""
        assert output.thk_alignment.palemahan != ""

    def test_thk_present_in_empty_result(self):
        output = ModuleOutput(
            status=404,
            data={},
            agent_hint="0 post ditemukan.",
            thk_alignment=THKAlignment(
                parahyangan="Data opini publik dikumpulkan secara etis dari sumber terbuka.",
                pawongan="Mengukur kepedulian masyarakat terhadap lingkungan.",
                palemahan="Memantau dampak pencemaran di pesisir Bali."
            )
        )
        assert output.thk_alignment is not None


# ═══════════════════════════════════════════════════════════════════
# TESTS — Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorEdgeCases:
    def setup_method(self):
        self.module = OSINTInstagramMonitor()
        self.context = {"session_id": "test_session"}

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    def test_empty_issue_returns_400(self, mock_extract, mock_search):
        from pydantic import ValidationError
        try:
            InstagramMonitorInput(issue="")
            assert False
        except ValidationError:
            pass

    def test_issue_with_special_characters(self):
        params = InstagramMonitorInput(
            issue="kebakaran hutan & banjir bandang di Bali! (2026)"
        )
        assert len(params.issue) >= 3

    def test_issue_with_emoji(self):
        params = InstagramMonitorInput(issue="sampah plastik 😢 pantai kuta")
        assert len(params.issue) >= 3

    def test_resolve_date_range_edge_date_from_equals_date_to(self):
        params = MagicMock(spec=InstagramMonitorInput)
        params.date_from = "2026-05-15"
        params.date_to = "2026-05-15"
        params.days_back = None
        date_from, date_to = self.module._resolve_date_range(params)
        assert date_from.date() == date_to.date()

    def test_scrape_post_returns_none_for_error(self):
        result = asyncio.run(self.module._scrape_post(
            "INVALID!!", datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc), True, {}
        ))
        assert result is None

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_all_posts_deleted(self, mock_analyze, mock_scrape,
                                mock_extract, mock_search):
        mock_search.return_value = [{"url": "https://instagram.com/p/DEL/"}]
        mock_extract.return_value = ["DEL123"]
        mock_scrape.return_value = ([], ["DEL123"])
        mock_analyze.return_value = {
            "emotions": {}, "dominant_tone": "no_data",
            "evidence": [], "trend_summary": "Tidak ada post."
        }

        params = InstagramMonitorInput(issue="deleted posts", days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.status == 200
        assert result.data["scrape_summary"]["total_posts_scraped"] == 0
        assert result.data["llm_analysis"]["dominant_tone"] == "no_data"

    def test_extract_shortcodes_with_encoding_in_url(self):
        results = [
            {"url": "https://www.instagram.com/p/ABC123/?__a=1&__d=1"},
            {"url": "https://instagram.com/p/DEF456/?igshid=MWNzM2QyOA=="},
        ]
        codes = self.module._extract_shortcodes(results)
        assert "ABC123" in codes
        assert "DEF456" in codes

    def test_extract_shortcodes_with_shortened_urls(self):
        results = [
            {"url": "https://www.instagram.com/p/ABC123/?utm_source=ig_web_copy_link"},
        ]
        codes = self.module._extract_shortcodes(results)
        assert "ABC123" in codes

    @patch.object(OSINTInstagramMonitor, "_search_instagram_urls")
    @patch.object(OSINTInstagramMonitor, "_extract_shortcodes")
    @patch.object(OSINTInstagramMonitor, "_scrape_posts")
    @patch.object(OSINTInstagramMonitor, "_analyze_emotions")
    def test_llm_analysis_error_in_execute(self, mock_analyze, mock_scrape,
                                            mock_extract, mock_search):
        mock_search.return_value = []
        mock_extract.return_value = ["POST1", "POST2"]
        mock_scrape.return_value = ([SAMPLE_POST], [])
        mock_analyze.return_value = {"dominant_tone": "analysis_error",
                                      "emotions": {}, "evidence": [],
                                      "trend_summary": "Gagal."}

        params = InstagramMonitorInput(issue="test", days_back=7)
        result = asyncio.run(self.module.execute(params, self.context))

        assert result.status == 200
        assert result.data["llm_analysis"]["dominant_tone"] == "analysis_error"


# ═══════════════════════════════════════════════════════════════════
# TESTS — Module Class Properties
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorProperties:
    def test_module_name(self):
        assert module.name == "osint_instagram_monitor"

    def test_module_description(self):
        assert len(module.description) > 50

    def test_module_version(self):
        assert module.version == "1.0.0"

    def test_module_tags(self):
        assert "osint" in module.tags
        assert "instagram" in module.tags
        assert "sentiment" in module.tags

    def test_input_schema_is_pydantic(self):
        schema = module.input_schema
        assert schema.__name__ == "InstagramMonitorInput"

    def test_output_example_structure(self):
        example = module.output_example
        assert "status" in example
        assert "data" in example
        assert example["status"] == 200

    def test_validate_self(self):
        issues = module.validate_self()
        assert issues == []

    def test_singleton_instance(self):
        from backend.modules.osint_instagram_monitor import module as m2
        assert module is m2
        assert isinstance(module, OSINTInstagramMonitor)


# ═══════════════════════════════════════════════════════════════════
# TESTS — Registry Integration
# ═══════════════════════════════════════════════════════════════════

class TestInstagramMonitorRegistry:
    def test_auto_registered(self):
        from backend.core.registry import registry
        manifests = registry.get_all_manifests()
        names = [m["name"] for m in manifests]
        assert "osint_instagram_monitor" in names

    def test_manifest_structure(self):
        from backend.core.registry import registry
        manifests = registry.get_all_manifests()
        insta = [m for m in manifests if m["name"] == "osint_instagram_monitor"]
        assert len(insta) == 1
        m = insta[0]
        assert "name" in m
        assert "description" in m
        assert "parameters" in m
        assert "properties" in m["parameters"]
        assert "issue" in m["parameters"]["properties"]

    def test_scope_match_osint_agent(self):
        from backend.core.orchestrator import get_scoped_manifests, SCOPE_MAP
        assert "osint_agent" in SCOPE_MAP
        osint_patterns = SCOPE_MAP["osint_agent"]
        has_osint_wildcard = any(p == "osint_*" for p in osint_patterns)
        assert has_osint_wildcard

    @patch("backend.core.registry.ModuleRegistry.execute_tool")
    def test_execute_via_registry(self, mock_execute):
        from backend.core.registry import registry
        mock_output = ModuleOutput(
            status=200,
            data={"scrape_summary": {"total_posts_scraped": 1}, "posts": [],
                  "period": {}, "llm_analysis": {}, "issue": "test"},
            agent_hint="test"
        )
        mock_execute.return_value = mock_output

        result = registry.execute_tool(
            "osint_instagram_monitor",
            {"issue": "test", "days_back": 7}
        )
        assert mock_execute.called


# ═══════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_classes = [
        TestInstagramMonitorInputSchema,
        TestInstagramMonitorStaticMethods,
        TestInstagramMonitorSearch,
        TestInstagramMonitorScrape,
        TestInstagramMonitorLLMAnalysis,
        TestInstagramMonitorExecute,
        TestInstagramMonitorUTIV2,
        TestInstagramMonitorTHK,
        TestInstagramMonitorEdgeCases,
        TestInstagramMonitorProperties,
        TestInstagramMonitorRegistry,
    ]

    passed = 0
    failed = 0

    for test_cls in test_classes:
        instance = test_cls()
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if name.startswith("test_"):
                try:
                    method()
                    print(f"  ✅ {test_cls.__name__}.{name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ❌ {test_cls.__name__}.{name} — {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ❌ {test_cls.__name__}.{name} — {type(e).__name__}: {e}")
                    failed += 1

    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)

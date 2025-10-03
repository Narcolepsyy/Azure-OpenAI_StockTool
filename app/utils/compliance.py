"""Financial compliance and guardrails utilities."""
import re
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import FINANCIAL_GUARDRAILS

logger = logging.getLogger(__name__)

# Investment advice detection patterns
INVESTMENT_ADVICE_PATTERNS = [
    r'(買い|売り|推奨|おすすめ|お勧め|オススメ)',
    r'(買う|売る|購入|売却)',
    r'(投資すべき|購入すべき|売るべき)',
    r'(今が買い時|今が売り時|買い時|売り時)',
    r'(アドバイス|助言|勧める)',
    r'(投資判断|トレード判断|投資決定)',
    r'(?i)(invest|buy|sell|recommend)',
    r'(?i)(should buy|should sell|purchase)',
    r'(?i)(good time to|right time to)',
    r'(?i)(advice|suggestion|recommendation)',
    r'(?i)(investment decision|trading decision)'
]

# Data confidence indicators
LOW_CONFIDENCE_INDICATORS = [
    "推定", "概算", "おそらく", "たぶん", "かもしれません",
    "estimated", "approximately", "probably", "might be", "could be"
]

class ComplianceValidator:
    """Validates responses for financial compliance requirements."""
    
    def __init__(self):
        self.guardrails = FINANCIAL_GUARDRAILS
    
    def validate_response(self, response: str, tool_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate response for compliance requirements.
        
        Returns:
            Dict with validation results and recommendations
        """
        validation_result = {
            "compliant": True,
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "enhanced_response": response
        }
        
        # Check for investment advice
        if self.guardrails.get("investment_advice_prohibited"):
            advice_violation = self._check_investment_advice(response)
            if advice_violation:
                validation_result["violations"].append(advice_violation)
                validation_result["compliant"] = False
        
        # Check for data source citations
        if self.guardrails.get("require_data_sources"):
            source_warning = self._check_data_sources(response, tool_results)
            if source_warning:
                validation_result["warnings"].append(source_warning)
        
        # Check for timezone and currency information
        if self.guardrails.get("require_timezone_currency"):
            timezone_warning = self._check_timezone_currency(response)
            if timezone_warning:
                validation_result["warnings"].append(timezone_warning)
        
        # Check confidence level
        if self.guardrails.get("require_confidence_threshold"):
            confidence_check = self._check_confidence_level(response)
            if confidence_check["low_confidence"]:
                validation_result["warnings"].append(confidence_check)
        
        # Generate enhanced response with compliance additions
        validation_result["enhanced_response"] = self._enhance_response_compliance(
            response, validation_result, tool_results
        )
        
        return validation_result
    
    def _check_investment_advice(self, response: str) -> Optional[Dict[str, Any]]:
        """Check if response contains prohibited investment advice."""
        for pattern in INVESTMENT_ADVICE_PATTERNS:
            if re.search(pattern, response):
                return {
                    "type": "investment_advice",
                    "message": "Response contains potential investment advice",
                    "severity": "high",
                    "recommendation": "Reframe as educational information with disclaimers"
                }
        return None
    
    def _check_data_sources(self, response: str, tool_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if data sources are properly cited."""
        has_data = tool_results and len(tool_results) > 0
        has_citations = any(word in response.lower() for word in [
            "出典", "ソース", "データ提供", "source", "data from", "according to"
        ])
        
        if has_data and not has_citations:
            return {
                "type": "missing_sources",
                "message": "データ出典が適切に記載されていません",
                "severity": "medium",
                "recommendation": "Add data source citations"
            }
        return None
    
    def _check_timezone_currency(self, response: str) -> Optional[Dict[str, Any]]:
        """Check if timezone and currency information is included."""
        has_timezone = any(tz in response for tz in [
            "JST", "Asia/Tokyo", "日本時間", "Tokyo", "東京"
        ])
        has_currency = any(curr in response for curr in [
            "JPY", "円", "¥", "日本円"
        ])
        
        missing = []
        if not has_timezone:
            missing.append("タイムゾーン")
        if not has_currency:
            missing.append("通貨")
        
        if missing:
            return {
                "type": "missing_metadata",
                "message": f"不足情報: {', '.join(missing)}",
                "severity": "medium",
                "recommendation": f"Add {', '.join(missing)} information"
            }
        return None
    
    def _check_confidence_level(self, response: str) -> Dict[str, Any]:
        """Check confidence level indicators in response."""
        low_confidence_count = sum(
            1 for indicator in LOW_CONFIDENCE_INDICATORS
            if indicator in response.lower()
        )
        
        return {
            "low_confidence": low_confidence_count > 0,
            "confidence_indicators": low_confidence_count,
            "type": "low_confidence",
            "message": f"Response contains {low_confidence_count} low confidence indicators",
            "severity": "low" if low_confidence_count < 2 else "medium",
            "recommendation": "Consider additional tool calls for higher confidence"
        }
    
    def _enhance_response_compliance(
        self, 
        response: str, 
        validation_result: Dict[str, Any], 
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Enhance response with compliance additions."""
        enhanced = response
        
        # Add disclaimer for investment advice concerns
        if any(v["type"] == "investment_advice" for v in validation_result["violations"]):
            disclaimer = "\n\n**免責事項**: この情報は教育目的のみで、投資助言ではありません。投資判断はご自身の責任で行ってください。"
            enhanced = disclaimer + enhanced
        
        # Add data source information
        if tool_results and not any(word in enhanced.lower() for word in ["出典", "source"]):
            sources = self._extract_data_sources(tool_results)
            if sources:
                source_text = "\n\n**データ出典**: " + ", ".join(sources)
                enhanced += source_text
        
        # Add timestamp and timezone if missing
        if not any(tz in enhanced for tz in ["JST", "Asia/Tokyo", "日本時間"]):
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            timestamp = f"\n\n**取得時刻**: {now.strftime('%Y年%m月%d日 %H:%M JST')}"
            enhanced += timestamp
        
        # Add confidence warning if needed
        confidence_check = next(
            (w for w in validation_result["warnings"] if w.get("type") == "low_confidence"),
            None
        )
        if confidence_check and confidence_check.get("confidence_indicators", 0) > 1:
            confidence_warning = "\n\n⚠️ **信頼度注意**: この回答には不確実な要素が含まれています。より正確な情報が必要な場合は、追加のデータ取得をお勧めします。"
            enhanced += confidence_warning
        
        return enhanced
    
    def _extract_data_sources(self, tool_results: List[Dict[str, Any]]) -> List[str]:
        """Extract data source information from tool results."""
        sources = []
        for result in tool_results or []:
            name = result.get("name", "")
            if name == "get_stock_quote":
                sources.append("Yahoo Finance")
            elif name == "get_historical_prices":
                sources.append("Yahoo Finance 履歴データ")
            elif name == "get_company_profile":
                sources.append("Yahoo Finance 企業情報")
            elif name in ["get_augmented_news", "get_nikkei_news"]:
                sources.append("ニュースAPI")
            elif name.startswith("web_search"):
                sources.append("Web検索")
        
        return list(set(sources))  # Remove duplicates


class DataValidator:
    """Validates data availability and quality."""
    
    @staticmethod
    def validate_realtime_data(data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Validate if realtime data is available and current."""
        validation = {
            "realtime_available": False,
            "data_age_minutes": None,
            "fallback_required": False,
            "message": ""
        }
        
        if not data or data.get("error"):
            validation["fallback_required"] = True
            validation["message"] = f"取得不可（{data.get('error', 'データエラー')}）"
            return validation
        
        # Check data timestamp
        timestamp_str = data.get("as_of") or data.get("timestamp")
        if timestamp_str:
            try:
                # Parse timestamp and calculate age
                if "T" in timestamp_str:
                    data_time = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    data_time = datetime.datetime.fromisoformat(timestamp_str)
                
                now = datetime.datetime.now(datetime.timezone.utc)
                age_minutes = (now - data_time).total_seconds() / 60
                
                validation["data_age_minutes"] = age_minutes
                validation["realtime_available"] = age_minutes < 30  # Consider real-time if < 30 minutes
                
                if not validation["realtime_available"]:
                    validation["fallback_required"] = True
                    validation["message"] = f"取得不可（データが{int(age_minutes)}分前のため）"
                
            except Exception as e:
                validation["fallback_required"] = True
                validation["message"] = f"取得不可（タイムスタンプ解析エラー: {e}）"
        else:
            validation["fallback_required"] = True
            validation["message"] = "取得不可（タイムスタンプなし）"
        
        return validation


def format_japanese_financial_data(
    data: Dict[str, Any], 
    data_type: str = "price",
    include_metadata: bool = True
) -> str:
    """Format financial data with Japanese compliance requirements."""
    
    if not data:
        return "データなし"
    
    formatted_lines = []
    
    # Format based on data type
    if data_type == "price":
        symbol = data.get("symbol", "N/A")
        price = data.get("price")
        currency = data.get("currency", "JPY")
        
        if price is not None:
            if currency == "JPY":
                formatted_lines.append(f"**{symbol}**: {price:,.0f}円")
            else:
                formatted_lines.append(f"**{symbol}**: {price:,.2f} {currency}")
    
    elif data_type == "company":
        name = data.get("longName", data.get("name", "N/A"))
        symbol = data.get("symbol", "N/A")
        sector = data.get("sector", "")
        industry = data.get("industry", "")
        
        formatted_lines.append(f"**{symbol} - {name}**")
        if sector or industry:
            sector_info = f"{sector}" + (f" / {industry}" if industry else "")
            formatted_lines.append(f"業種: {sector_info}")
    
    # Add metadata if required
    if include_metadata:
        # Timestamp
        timestamp = data.get("as_of") or data.get("timestamp")
        if timestamp:
            if "T" in timestamp:
                # Convert to JST
                try:
                    dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    jst_dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
                    formatted_lines.append(f"取得時刻: {jst_dt.strftime('%Y年%m月%d日 %H:%M JST')}")
                except:
                    formatted_lines.append(f"取得時刻: {timestamp}")
            else:
                formatted_lines.append(f"取得時刻: {timestamp}")
        
        # Currency (if not already mentioned)
        currency = data.get("currency")
        if currency and currency not in str(formatted_lines):
            formatted_lines.append(f"通貨: {currency}")
    
    return "\n".join(formatted_lines)


# Global compliance validator instance
compliance_validator = ComplianceValidator()
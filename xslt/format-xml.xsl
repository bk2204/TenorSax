<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
	xmlns:t="http://ns.crustytoothpaste.net/troff"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" encoding="UTF-8"/>
	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>
	<xsl:template match="t:*">
		<xsl:if test="text()">
			<xsl:message terminate="yes">stray text not allowed</xsl:message>
		</xsl:if>
		<xsl:if test="(count(*) - count(t:*)) > 1">
			<xsl:message terminate="yes">
				<xsl:text>multiple root elements not allowed</xsl:text>
			</xsl:message>
		</xsl:if>
		<xsl:apply-templates select="node()"/>
	</xsl:template>
</xsl:stylesheet>

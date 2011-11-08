<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
	xmlns:t="http://ns.crustytoothpaste.net/troff"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="text" encoding="UTF-8"/>
	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>
	<xsl:template match="t:main">
		<xsl:apply-templates select="*"/>
	</xsl:template>
	<xsl:template match="t:break-page"/>
	<xsl:template match="t:block">
		<xsl:variable name="content" select="string(.)"/>
		<xsl:variable name="ncontent" select="normalize-space($content)"/>
		<xsl:variable name="last" select="substring($content, string-length($content))"/>
		<xsl:choose>
			<xsl:when test="string-length($ncontent) = 0">
			</xsl:when>
			<!--
			<xsl:when test="$last = ' '">
				<xsl:value-of select="concat(substring($content, 1, string-length($content)-1), '&#xa;')"/>
			</xsl:when>
			-->
			<xsl:otherwise>
				<xsl:value-of select="concat($ncontent, '&#xa;')"/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>
</xsl:stylesheet>

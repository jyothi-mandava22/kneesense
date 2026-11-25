package com.kneesense.domain;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

import java.util.Locale;

@Converter
public class PredictionSourceConverter implements AttributeConverter<PredictionSource, String> {

    @Override
    public String convertToDatabaseColumn(PredictionSource attribute) {
        return attribute == null ? null : attribute.name().toLowerCase(Locale.ROOT);
    }

    @Override
    public PredictionSource convertToEntityAttribute(String dbData) {
        return dbData == null ? null : PredictionSource.valueOf(dbData.toUpperCase(Locale.ROOT));
    }
}

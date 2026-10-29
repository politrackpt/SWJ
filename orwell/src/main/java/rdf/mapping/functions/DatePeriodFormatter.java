package rdf.mapping.functions;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

public class DatePeriodFormatter {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE;

    public static String toIso8601Period(String startDate, String endDate) {
        if (startDate == null || startDate.trim().isEmpty()) {
            return null;
        }

        String normalizedStart = normalizeDate(startDate);

        if (endDate == null || endDate.trim().isEmpty()) {
            return normalizedStart;
        }

        String normalizedEnd = normalizeDate(endDate);

        return normalizedStart + "/" + normalizedEnd;
    }

    private static String normalizeDate(String date) {
        String normalizedDate = date.trim();

        try {
            return LocalDate.parse(normalizedDate, DATE_FORMATTER).toString();
        } catch (DateTimeParseException ignored) { }

        try {
            return LocalDateTime.parse(normalizedDate).toLocalDate().toString();
        } catch (DateTimeParseException ignored) { }

        try {
            DateTimeFormatter dateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.S");
            return LocalDateTime.parse(normalizedDate, dateTimeFormatter).toLocalDate().toString();
        } catch (DateTimeParseException exception) {
            throw new IllegalArgumentException("Unsupported date format: " + normalizedDate, exception);
        }
    }
}

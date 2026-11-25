package com.kneesense.ml;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.time.Duration;

/** Real HTTP client. Enabled only after the team is ready to switch from the mock. */
@Component
@ConditionalOnProperty(name = "app.ml.mode", havingValue = "http")
public class HttpMlPredictionClient implements MlPredictionClient {

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String sharedSecret;

    public HttpMlPredictionClient(
        ObjectMapper objectMapper,
        @Value("${ML_SERVICE_URL}") String serviceUrl,
        @Value("${ML_SERVICE_SECRET}") String sharedSecret,
        @Value("${app.ml.timeout-ms:90000}") long timeoutMs
    ) {
        if (serviceUrl == null || serviceUrl.isBlank() || sharedSecret == null || sharedSecret.isBlank()) {
            throw new IllegalStateException("ML service URL and shared secret are required in HTTP mode.");
        }
        if (timeoutMs < 1) {
            throw new IllegalStateException("ML timeout must be a positive number of milliseconds.");
        }

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(5));
        requestFactory.setReadTimeout(Duration.ofMillis(timeoutMs));

        this.restClient = RestClient.builder()
            .baseUrl(serviceUrl.replaceAll("/$", ""))
            .requestFactory(requestFactory)
            .build();
        this.objectMapper = objectMapper;
        this.sharedSecret = sharedSecret;
    }

    @Override
    public MlPredictionResponse predict(byte[] imageBytes, MediaType mediaType, String filename) {
        return predict(imageBytes, mediaType, filename, false);
    }

    @Override
    public MlPredictionResponse predict(
        byte[] imageBytes,
        MediaType mediaType,
        String filename,
        boolean forceCachedReports
    ) {
        MultiValueMap<String, Object> multipart = new LinkedMultiValueMap<>();
        ByteArrayResource image = new ByteArrayResource(imageBytes) {
            @Override
            public String getFilename() {
                return filename;
            }
};

HttpHeaders partHeaders = new HttpHeaders();
partHeaders.setContentDispositionFormData("file", filename);
partHeaders.setContentType(mediaType);

multipart.add("file", new HttpEntity<>(image, partHeaders));
        try {
            return restClient.post()
                .uri("/predict")
                .header("X-Internal-Auth", sharedSecret)
                .header("X-Force-Cached-Reports", Boolean.toString(forceCachedReports))
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(multipart)
                .exchange((request, response) -> {
                    try (InputStream body = response.getBody()) {
                        if (response.getStatusCode().is2xxSuccessful()) {
                            MlPredictionResponse prediction = objectMapper.readValue(body, MlPredictionResponse.class);
                            if (prediction == null) {
                                throw MlServiceException.forCode("internal_error");
                            }
                            return prediction;
                        }
                        MlErrorResponse error = objectMapper.readValue(body, MlErrorResponse.class);
                        if (response.getStatusCode().value() == 401) {
                            throw MlServiceException.forCode("unauthorized");
                        }
                        throw MlServiceException.forCode(error == null ? "internal_error" : error.error());
                    }
                });
        } catch (MlServiceException ex) {
            throw ex;
        } catch (ResourceAccessException ex) {
            throw MlServiceException.forCode("model_unavailable");
        } catch (RestClientException ex) {
            throw MlServiceException.forCode("internal_error");
        }
    }
}

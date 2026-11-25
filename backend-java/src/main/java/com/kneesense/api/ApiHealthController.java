package com.kneesense.api;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ApiHealthController {

    @GetMapping("/health")
    public ApiHealthResponse health() {
        return new ApiHealthResponse("UP", "KneeSense backend", "foundation");
    }

    public record ApiHealthResponse(String status, String application, String stage) {
    }
}

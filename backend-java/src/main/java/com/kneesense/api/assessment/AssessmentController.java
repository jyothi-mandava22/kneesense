package com.kneesense.api.assessment;

import com.kneesense.api.assessment.dto.AssessmentDetailResponse;
import com.kneesense.api.assessment.dto.AssessmentSummaryResponse;
import com.kneesense.api.assessment.dto.AssessmentUploadResponse;
import com.kneesense.security.AppUserPrincipal;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/assessments")
public class AssessmentController {

    private final AssessmentService assessmentService;

    public AssessmentController(AssessmentService assessmentService) {
        this.assessmentService = assessmentService;
    }

    @PostMapping(consumes = "multipart/form-data")
    public AssessmentUploadResponse upload(
        @AuthenticationPrincipal AppUserPrincipal principal,
        @RequestParam("file") MultipartFile file
    ) {
        return assessmentService.upload(principal.getId(), file);
    }

    @GetMapping
    public List<AssessmentSummaryResponse> listMine(
        @AuthenticationPrincipal AppUserPrincipal principal
    ) {
        return assessmentService.listMyAssessments(principal.getId());
    }

    @GetMapping("/{resultId}")
    public AssessmentDetailResponse getMine(
        @AuthenticationPrincipal AppUserPrincipal principal,
        @PathVariable Long resultId
    ) {
        return assessmentService.getMyAssessment(principal.getId(), resultId);
    }
}

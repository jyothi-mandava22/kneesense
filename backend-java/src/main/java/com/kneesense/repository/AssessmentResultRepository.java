package com.kneesense.repository;

import com.kneesense.domain.AssessmentResult;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AssessmentResultRepository extends JpaRepository<AssessmentResult, Long> {

    Optional<AssessmentResult> findByIdAndUpload_User_Id(Long resultId, Long userId);

    Optional<AssessmentResult> findByUpload_Id(Long uploadId);

    List<AssessmentResult> findAllByUpload_User_IdOrderByCreatedAtDesc(Long userId);
}

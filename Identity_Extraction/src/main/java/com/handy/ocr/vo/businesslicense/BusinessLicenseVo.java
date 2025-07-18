package com.handy.ocr.vo.businesslicense;

import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {营业职照识别结果}
 * @date 2019/9/10
 */
@Data
public class BusinessLicenseVo implements Serializable{
    /**
     * 唯一的log id，用于问题定位
     */
    private long log_id;
    /**
     * 定位和识别结果数组
     */
    private WordsResult words_result;
    /**
     * 识别结果数，表示words_result的元素个数
     */
    private int words_result_num;
}

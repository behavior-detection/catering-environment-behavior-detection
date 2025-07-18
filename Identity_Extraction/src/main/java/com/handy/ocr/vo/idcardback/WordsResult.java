package com.handy.ocr.vo.idcardback;

import com.handy.ocr.vo.Words;
import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {身份背面证识别结果}
 * @date 2019/9/10
 */
@Data
public class WordsResult implements Serializable {

    /**
     * 失效日期
     */
    private Words expiryDate;
    /**
     * 签发机关
     */
    private Words issuingSuthority;
    /**
     * 签发日期
     */
    private Words issuingDate;
}
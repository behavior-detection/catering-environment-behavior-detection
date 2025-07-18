package com.handy.ocr.vo.idcardfront;

import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {身份证正面识别结果}
 * @date 2019/9/10
 */
@Data
public class IdCardFrontVo implements Serializable {
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
    /**
     * normal-识别正常
     * reversed_side-身份证正反面颠倒
     * non_idcard-上传的图片中不包含身份证
     * blurred-身份证模糊
     * other_type_card-其他类型证照
     * over_exposure-身份证关键字段反光或过曝
     * over_dark-身份证欠曝（亮度过低）
     * unknown-未知状态
     */
    private String image_status;
    /**
     * 图像方向，当 detect_direction = true 时，返回该参数。
     * - -1:未定义，
     * - 0:正向，
     * - 1: 逆时针90度，
     * - 2:逆时针180度，
     * - 3:逆时针270度
     */
    private int direction;
}
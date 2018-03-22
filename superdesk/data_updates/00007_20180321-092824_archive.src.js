// building:
// copy the contents to client-core index file
// change webpack config, add target: 'node', to the exported object
// run grunt build

import {convertFromRaw, convertToRaw, EditorState, SelectionState, Modifier} from 'draft-js';
import {addHighlight, prepareHighlightsForExport} from './core/editor3/helpers/highlights';

function removeCustomDataFieldFromEditor(editorState, key) {
    const currentSelectionToPreserve = editorState.getSelection();

    let contentState = editorState.getCurrentContent();
    const currentData = contentState.getFirstBlock().getData();
    const dataWithKeyRemoved = currentData.remove(key);

    const firstBlockSelection = SelectionState.createEmpty(contentState.getFirstBlock().getKey());

    contentState = Modifier.setBlockData(contentState, firstBlockSelection, dataWithKeyRemoved);

    const editorStateWithNewDataSet = EditorState.push(editorState, contentState, 'change-block-data');

    const editorStateWithSelectionRestored = EditorState.forceSelection(
        editorStateWithNewDataSet,
        currentSelectionToPreserve
    );

    return editorStateWithSelectionRestored;
}

function convertAnnotationsToNewFormat(rawContentState) {
    const initialEditorState = EditorState.createWithContent(convertFromRaw(rawContentState));

    const firstBlockData = initialEditorState
        .getCurrentContent()
        .getFirstBlock()
        .getData()
        .toJS();

    const editorStateWithAnnotationsConverted = Object.keys(firstBlockData).reduce((editorState, firstBlockDataKey) => {
        const value = firstBlockData[firstBlockDataKey];
        var parsedDataKey = null;

        try {
            parsedDataKey = JSON.parse(firstBlockDataKey);
        } catch (e) {
            // not an old comment or annotation
            return editorState;
        }

        if (parsedDataKey === null || value.type !== 'ANNOTATION') {
            return editorState;
        }

        // set selection from old annotation JSON
        const editorWithSelection = EditorState.acceptSelection(
            editorState,
            new SelectionState(parsedDataKey)
        );

        const editorStateWithHighlightAdded = addHighlight(editorWithSelection, value.type, {
            type: value.type,
            data: value
        });

        const editorStateWithOldKeyRemoved =
            removeCustomDataFieldFromEditor(editorStateWithHighlightAdded, firstBlockDataKey);

        return editorStateWithOldKeyRemoved;
    }, initialEditorState);

    const exportState = convertToRaw(
        prepareHighlightsForExport(editorStateWithAnnotationsConverted).getCurrentContent()
    );

    return exportState;
}

function isDraftJsRawState(obj) {
    return typeof obj === 'object'
        && Object.keys(obj).length === 2
        && Object.keys(obj).includes('entityMap')
        && Object.keys(obj).includes('blocks');
}

// pipe the result to stdout

var stdin = process.openStdin();

var inputData = '';

stdin.on('data', (chunk) => {
    inputData = chunk.toString();
});

stdin.on('end', () => {
    let inputDataJson = null;

    try {
        inputDataJson = JSON.parse(inputData);
    } catch (e) {
        // return input onchanged
        return process.stdout.write(inputData);
    }

    if (
        Array.isArray(inputDataJson)
        && inputDataJson.length === 1
        && isDraftJsRawState(inputDataJson[0])
    ) {
        const result = convertAnnotationsToNewFormat(inputDataJson[0]);
        const resultWrappedInArray = [result];

        return process.stdout.write(JSON.stringify(resultWrappedInArray));
    } else {
        // return input onchanged
        return process.stdout.write(inputData);
    }
});
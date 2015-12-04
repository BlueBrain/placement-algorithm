%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function Layer = getLayerDefinition(recipe)
% define Layer Boundaries

ifElseExpansion = @(x,ie)ie{double(x)+1};            
nameFieldLookup = @(x,str,fn)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(find(cellfun(@(s)strcmp(s,str),{x.Name}),1,'last')).(fn)});

if(exist('parseXML','file'))
    xml = parseXML(recipe);
else
    xml = xml2struct(recipe);
end

column = nameFieldLookup(xml,'blueColumn','Children');
column = nameFieldLookup(column,'column','Children');

layers = column(cellfun(@(x)strcmp(x,'layer'),{column.Name}));
for i = 1:length(layers)
    layerNum = str2double(nameFieldLookup(layers(i).Attributes,'id','Value'));
    thickness(layerNum) = str2double(nameFieldLookup(layers(i).Attributes,'thickness','Value'));
end

maxLayer = length(thickness);
currMin = 0;

for i = maxLayer:-1:1
    Layer(i).From = currMin;
    Layer(i).To = currMin + thickness(i);
    currMin = Layer(i).To;
end

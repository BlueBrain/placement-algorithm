classdef XmlSpecifiedRuleCheck < handle
    %XMLSPECIFIEDRULECHECK This class is doing the parsing of placement rules defined
    %in xml format and then checks individual cells.    
    
    properties(Access=private)
        ruleSetFile;
        ruleSets;
        
        morphologyRuleInstances;
        layerInfo;
        
        results;
        
        yBinsSize; %TODO: offer set function
        layerBins;
        transferFcn;
    end
    properties(Access=public)
        strictness;
    end
    
    methods
        function obj = XmlSpecifiedRuleCheck(file,lInfo)
            obj.ruleSetFile = file;
            obj.layerInfo = lInfo;
            obj.yBinsSize = 10; %micron
            obj.transferFcn.id = @(x)x;
            obj.makeLayerBins();
            %then do parsing here            
            xml = parseXML(file);
            obj.addRulesFromXml(xml);
        end
        function [] = addMorphologyInstance(obj,file)
            %read new rule instances
            xml =  parseXML(file);            
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameFieldLookup = @(x,str,fn)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).(fn)});
            morphName = 'foobar';%nameValueLookup(xml.Attributes,'morphology');
            annotations = xml.Children;
            annotations = annotations(cellfun(@(x)strcmp(x,'placement'),{annotations.Name}));
            for i = 1:length(annotations)
                instance = nameFieldLookup(annotations(i).Children,'use_rule','Attributes');
                ruleName = nameFieldLookup(instance,'rule','Value');
                %Right now we only consider y intervals. Any other cases
                %planned?
                y_min = str2double(nameFieldLookup(instance,'y_min','Value'));
                y_max = str2double(nameFieldLookup(instance,'y_max','Value'));
                obj.morphologyRuleInstances.(morphName)(i).Rule = ruleName;
                obj.morphologyRuleInstances.(morphName)(i).Interval = [y_min y_max];
            end            
        end
        function scores = getResult(obj,morphName,inLayer,asMType)            
            scores = obj.checkMorphology(morphName,inLayer,asMType);            
            obj.results(end+1).morphology = morphName;
            obj.results(end).mtype = asMType;
            obj.results(end).scores = scores;
            obj.results(end).layer = inLayer;
        end
        function [] = plotOverview(obj,varargin)
            
        end
    end
    methods(Access=private)        
        function scores = checkMorphology(obj,morphName,inLayer,asMType)
            if(~isfield(obj.morphologyRuleInstances,morphName))
                error('PlacementHints:getResults:MorphologyNotAnnotated','Morphology %s has no rule instance file specified!',morphName);
            else
                if(~isfield(obj.ruleSets,asMType))
                    error('PlacementHints:getResults:MTypeNotKnown','Cannot find rules for MType %s!',asMType);
                end
                relevantInstances = obj.morphologyRuleInstances.(morphName);
                relevantRuleSet = obj.ruleSets.(asMType);                
                for i = 1:length(relevantInstances)
                    scores(i,:) = obj.checkRuleInstance(relevantInstances(i),relevantRuleSet,obj.layerBins{inLayer});
                end
                scores = mergeScores(scores);
            end
        end
        function scores = checkRuleInstance(obj,instance,set,bins)
            if(~isfield(set,instance.Rule))
                error('PlacementHints:getResults:UnknownRule','Rule instance refers to rule %s in %s, which is not defined!',...
                    instance.Rule,set.mtype);
            end
            minMaxFcn = @(x,y)cat(2,max(x(1),y(1)),min(x(2),y(2)));
            intervalAbs = obj.getLayerInterval(set.(instance.Rule));            
            scores = cellfun(@(x)diff(minMaxFcn(intervalAbs,instance.Interval+x)),num2cell(bins))./min(diff(intervalAbs),diff(instance.Interval));
            scores(scores<0)=0;
            if(isfield(instance,'transferFcn'))
                scores = obj.transferFcn.(instance.transferFcn)(scores);
            end
        end
        function scores = mergeScores(obj,scores)  
            fcn = @(x,p)((sum(x.^p)/length(x))^(1/p));
            shapeParameter = norminv(obj.strictness/101,1,2.25);            
            baseWeight = size(scores,1).*(log10(obj.strictness)^((obj.strictness)./10));
            scores = baseWeight.*cellfun(@(x)fcn(x,shapeParameter),num2cell(scores,1))+ones(1,size(scores,2));
        end
        
        %Function subject to change if we ever inplement more than just y
        %intervals. For now lazily implemented
        function interval = getLayerInterval(obj,rule)
            fractionLookup = @(iv,f)iv(1)+f*diff(iv);
            getIv = @(x)cat(2,obj.layerInfo(x).From,obj.layerInfo(x).To);
            
            l = cat(1,str2double(rule.y_min_layer), str2double(rule.y_max_layer));
            f = cat(1,str2double(rule.y_min_fraction), str2double(rule.y_max_fraction));
            interval = cat(2,fractionLookup(getIv(l(1)),f(1)),fractionLookup(getIv(l(2)),f(2)));
        end                      
        
        function [] = addRulesFromXml(obj,xml)
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameValueLookup = @(x,str)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).Value});
            
            for i = 1:length(xml)
                currMType = nameValueLookup(xml(i).Attributes,'mtype');
                obj.ruleSets.(currMType).mtype = currMType;
                %If we ever have other types of rules add that case here.
                rules = xml(i).Children;
                rules = rules(cellfun(@(x)x(1)~='#',{rules.Name}));
                for j = 1:length(rules)
                    id = nameValueLookup(rules(j).Attributes,'id');
                    if(isempty(id))
                        error('XMLPlacementHints:Rules:EmptyIdentifier','This rule has no field "id" specified!');
                    end
                    attr = setdiff({rules(j).Attributes.Name},'id');
                    for k=1:length(attr)
                        obj.ruleSets.(currMType).(id).(attr{k}) = nameValueLookup(rules(j).Attributes,attr{k});
                    end
                end
            end
        end
        
        function [] = makeLayerBins(obj)            
            for i = 1:length(obj.layerInfo)
                borders = linspace(obj.layerInfo(i).From,obj.layerInfo(i).To,...
                    ceil((obj.layerInfo(i).To-obj.layerInfo(i).From)/obj.yBinsSize)+1);
                obj.layerBins{i} = (borders(1:end-1) + borders(2:end))./2;
            end
        end
    end
end

